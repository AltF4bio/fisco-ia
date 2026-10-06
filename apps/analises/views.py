from datetime import datetime

from django.contrib import messages
from django.http import Http404, HttpResponse
from django.shortcuts import redirect, render
from django.utils.text import slugify
from django.views import View
from django.views.generic import FormView, TemplateView

from apps.analises.forms import NovaAnaliseForm, RespostasForm
from apps.analises.services import exportacao, fluxo, sessao
from apps.analises.services.qualidade import QualidadeExtracao
from apps.auditoria.services import Acao, registrar
from apps.core.markdown_seguro import para_html
from apps.core.permissoes import ProcuradorMixin


class NovaAnaliseView(ProcuradorMixin, FormView):
    template_name = "analises/nova.html"
    form_class = NovaAnaliseForm

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        contexto["resultados"] = sessao.listar_resultados(self.request.session)
        return contexto

    def form_valid(self, form):
        arquivo = form.cleaned_data["arquivo"]
        try:
            resultado = fluxo.iniciar(
                self.request,
                arquivo,
                form.cleaned_data["agente"],
                form.cleaned_data["numero_processo"],
            )
        finally:
            arquivo.close()  # descarta o upload (memória ou arquivo temporário)

        if resultado.etapa == "concluido":
            return redirect("analises:resultado", identificador=resultado.resultado_id)
        if resultado.etapa == "perguntas":
            return redirect("analises:perguntas")
        inicial = {
            "agente": form.cleaned_data["agente"],
            "numero_processo": form.cleaned_data["numero_processo"],
        }
        contexto = self.get_context_data(form=self.form_class(initial=inicial))
        contexto["recusa" if resultado.etapa == "recusado" else "erro"] = resultado
        return self.render_to_response(contexto)


class PerguntasView(ProcuradorMixin, View):
    template_name = "analises/perguntas.html"

    def _pendente(self):
        pendente = sessao.obter_pendente(self.request.session)
        if pendente is None:
            messages.info(self.request, "Não há análise aguardando esclarecimentos.")
        return pendente

    def get(self, request):
        pendente = self._pendente()
        if pendente is None:
            return redirect("analises:nova")
        return self._render(pendente, RespostasForm(perguntas=pendente["perguntas"]))

    def post(self, request):
        pendente = self._pendente()
        if pendente is None:
            return redirect("analises:nova")
        if "cancelar" in request.POST:
            sessao.cancelar_pendente(request.session)
            messages.info(request, "Análise cancelada. O texto dos autos foi descartado.")
            return redirect("analises:nova")
        form = RespostasForm(request.POST, perguntas=pendente["perguntas"])
        if not form.is_valid():
            return self._render(pendente, form)
        resultado = fluxo.responder(request, form.cleaned_data)
        if resultado.etapa == "concluido":
            return redirect("analises:resultado", identificador=resultado.resultado_id)
        messages.error(request, resultado.mensagem)
        return redirect("analises:nova")

    def _render(self, pendente, form):
        return render(
            self.request,
            self.template_name,
            {
                "pendente": pendente,
                "form": form,
                "qualidade": QualidadeExtracao.de_dict(pendente["qualidade"]),
            },
        )


class _ResultadoMixin(ProcuradorMixin):
    def obter(self, identificador: str) -> dict:
        resultado = sessao.obter_resultado(self.request.session, identificador)
        if resultado is None:
            raise Http404("Análise não encontrada nesta sessão.")
        return resultado


class ResultadoView(_ResultadoMixin, TemplateView):
    template_name = "analises/resultado.html"

    def get_context_data(self, identificador: str, **kwargs):
        resultado = self.obter(identificador)
        return {
            **super().get_context_data(**kwargs),
            "identificador": identificador,
            "resultado": resultado,
            "criado_em": datetime.fromisoformat(resultado["criado_em"]),
            "html": para_html(resultado["texto"]),
            "qualidade": QualidadeExtracao.de_dict(resultado["qualidade"]),
        }


class ExportarPDFView(_ResultadoMixin, View):
    def get(self, request, identificador: str):
        resultado = self.obter(identificador)
        usuario = request.user.get_full_name() or request.user.get_username()
        conteudo = exportacao.analise_em_pdf(resultado, exportado_por=usuario)
        registrar(
            Acao.EXPORTACAO,
            request=request,
            numero_processo=resultado.get("numero_processo", ""),
            agente=resultado["agente"],
            provedor=resultado["provedor"],
            modelo=resultado["modelo"],
            objeto="Análise exportada em PDF",
        )
        nome = slugify(f"fisco-ia-{resultado['agente_slug']}-{resultado.get('numero_processo')}")
        resposta = HttpResponse(conteudo, content_type="application/pdf")
        resposta["Content-Disposition"] = f'attachment; filename="{nome}.pdf"'
        return resposta
