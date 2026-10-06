from django.contrib import messages
from django.db.models import Count, Sum
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.utils.text import slugify
from django.views import View
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView

from apps.auditoria.services import Acao, registrar
from apps.core.permissoes import ProcuradorMixin
from apps.empresas.forms import EmpresaForm, EnvioExecucoesForm, ExecucaoRevisaoForm
from apps.empresas.models import Empresa, ExecucaoFiscal, Situacao
from apps.empresas.services import consolidacao, tabela


class EmpresaListView(ProcuradorMixin, ListView):
    template_name = "empresas/lista.html"
    context_object_name = "empresas"
    paginate_by = 25

    def get_queryset(self):
        qs = Empresa.objects.annotate(
            total_execucoes=Count("execucoes"), valor_total=Sum("execucoes__valor_executado")
        )
        busca = self.request.GET.get("busca", "").strip()
        if busca:
            qs = qs.filter(razao_social__icontains=busca) | qs.filter(
                cnpj__icontains=busca.replace(".", "").replace("/", "").replace("-", "")
            )
        return qs.order_by("razao_social")


class _EmpresaFormMixin(ProcuradorMixin):
    model = Empresa
    form_class = EmpresaForm
    template_name = "empresas/form.html"
    verbo = ""

    def get_success_url(self):
        return reverse("empresas:detalhe", args=[self.object.pk])

    def form_valid(self, form):
        if not form.instance.pk:
            form.instance.criado_por = self.request.user
        resposta = super().form_valid(form)
        registrar(Acao.CADASTRO_EMPRESA, request=self.request,
                  objeto=f"Empresa #{self.object.pk} {self.verbo}")  # fmt: skip
        messages.success(self.request, f"Empresa {self.verbo}.")
        return resposta


class EmpresaCreateView(_EmpresaFormMixin, CreateView):
    verbo = "cadastrada"


class EmpresaUpdateView(_EmpresaFormMixin, UpdateView):
    verbo = "alterada"


class EmpresaDeleteView(ProcuradorMixin, DeleteView):
    model = Empresa
    template_name = "empresas/confirmar_exclusao.html"
    success_url = reverse_lazy("empresas:lista")

    def form_valid(self, form):
        pk = self.object.pk
        resposta = super().form_valid(form)
        registrar(Acao.CADASTRO_EMPRESA, request=self.request, objeto=f"Empresa #{pk} excluída")
        messages.success(self.request, "Empresa excluída.")
        return resposta


class EmpresaDetailView(ProcuradorMixin, DetailView):
    """Dados da empresa, envio de PDFs e tabela consolidada (filtros via HTMX)."""

    model = Empresa
    template_name = "empresas/detalhe.html"

    def get_template_names(self):
        if self.request.headers.get("HX-Request"):
            return ["empresas/_tabela.html"]
        return [self.template_name]

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        filtros = tabela.Filtros.de_query(self.request.GET)
        execucoes = tabela.consultar(self.object, filtros)
        contexto.update(
            filtros=filtros,
            execucoes=execucoes,
            totais=tabela.totais(execucoes),
            situacoes=Situacao.choices,
            form_envio=kwargs.get("form_envio") or EnvioExecucoesForm(),
            query=self.request.GET.urlencode(),
        )
        return contexto


class EnviarExecucoesView(ProcuradorMixin, View):
    def post(self, request, pk):
        empresa = get_object_or_404(Empresa, pk=pk)
        form = EnvioExecucoesForm(request.POST, request.FILES)
        if not form.is_valid():
            for erro in form.errors.get("arquivos", []):
                messages.error(request, erro)
            return redirect("empresas:detalhe", pk=pk)

        for arquivo in form.cleaned_data["arquivos"]:
            try:
                resultado = consolidacao.processar_pdf(request, empresa, arquivo)
            except consolidacao.ConsolidacaoError as erro:
                messages.error(request, f"{arquivo.name}: {erro}")
                continue
            finally:
                arquivo.close()
            acao = "incluído na" if resultado.criada else "atualizado na"
            mensagem = f"{arquivo.name}: processo {resultado.execucao} {acao} tabela."
            if resultado.campos_preservados:
                mensagem += " Campos revisados manualmente foram preservados."
            if resultado.qualidade.baixa:
                messages.warning(
                    request,
                    f"{mensagem} Atenção: baixa qualidade de extração "
                    f"({resultado.qualidade.percentual}%) — o PDF pode estar digitalizado sem OCR, "
                    "manuscrito ou corrompido; confira os dados.",
                )
            else:
                messages.success(request, mensagem)
        return redirect("empresas:detalhe", pk=pk)


class ExecucaoRevisaoView(ProcuradorMixin, UpdateView):
    model = ExecucaoFiscal
    form_class = ExecucaoRevisaoForm
    template_name = "empresas/revisao.html"
    context_object_name = "execucao"

    def form_valid(self, form):
        original = ExecucaoFiscal.objects.get(pk=self.object.pk)
        alterados = form.campos_alterados(original)
        if not alterados:
            messages.info(self.request, "Nenhum campo foi alterado.")
            return redirect("empresas:detalhe", pk=self.object.empresa_id)
        execucao = form.save(commit=False)
        execucao.campos_revisados = sorted(set(execucao.campos_revisados) | set(alterados))
        execucao.revisado_manualmente = True
        execucao.save()
        registrar(
            Acao.REVISAO_EXECUCAO,
            request=self.request,
            numero_processo=execucao.numero_processo,
            objeto=f"Campos revisados: {', '.join(alterados)}",
        )
        messages.success(self.request, "Revisão salva. Os campos corrigidos prevalecem sobre a IA.")
        return redirect("empresas:detalhe", pk=execucao.empresa_id)


class ExportarTabelaView(ProcuradorMixin, View):
    def get(self, request, pk, formato):
        if formato not in ("csv", "pdf"):
            raise Http404("Formato de exportação não suportado.")
        empresa = get_object_or_404(Empresa, pk=pk)
        filtros = tabela.Filtros.de_query(request.GET)
        execucoes = tabela.consultar(empresa, filtros)
        nome = slugify(f"fisco-ia-execucoes-{empresa.razao_social}")[:80]
        if formato == "csv":
            resposta = HttpResponse(
                tabela.exportar_csv(empresa, execucoes), content_type="text/csv; charset=utf-8"
            )
        else:
            resposta = HttpResponse(
                tabela.exportar_pdf(empresa, execucoes, filtros), content_type="application/pdf"
            )
        resposta["Content-Disposition"] = f'attachment; filename="{nome}.{formato}"'
        registrar(
            Acao.EXPORTACAO,
            request=request,
            objeto=f"Tabela consolidada da empresa #{empresa.pk} ({formato.upper()})",
        )
        return resposta
