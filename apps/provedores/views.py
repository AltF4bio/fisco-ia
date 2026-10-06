from django.contrib import messages
from django.shortcuts import get_object_or_404, render
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import CreateView, ListView, UpdateView

from apps.auditoria.services import Acao, Resultado, registrar
from apps.core.permissoes import AdministradorMixin
from apps.provedores import services
from apps.provedores.forms import ModeloIAForm, ProvedorForm
from apps.provedores.models import ModeloIA, ProvedorIA


class ProvedorListView(AdministradorMixin, ListView):
    template_name = "provedores/lista.html"
    context_object_name = "provedores"

    def get_queryset(self):
        return ProvedorIA.objects.prefetch_related("modelos")


class ProvedorUpdateView(AdministradorMixin, UpdateView):
    model = ProvedorIA
    form_class = ProvedorForm
    template_name = "provedores/form.html"
    context_object_name = "provedor"
    success_url = reverse_lazy("provedores:lista")

    def form_valid(self, form):
        resposta = super().form_valid(form)
        alteracoes = ", ".join(form.changed_data) or "sem alterações"
        registrar(
            Acao.CADASTRO_PROVEDOR,
            request=self.request,
            provedor=self.object.tipo,
            objeto=f"Provedor alterado ({alteracoes})",
        )
        messages.success(self.request, f"Provedor {self.object} atualizado.")
        return resposta


class TestarConexaoView(AdministradorMixin, View):
    """Testa a conexão com o provedor (requisição HTMX) e devolve o resultado."""

    def post(self, request, pk):
        provedor = get_object_or_404(ProvedorIA, pk=pk)
        sucesso, mensagem = services.testar_conexao(provedor)
        registrar(
            Acao.TESTE_PROVEDOR,
            request=request,
            provedor=provedor.tipo,
            resultado=Resultado.SUCESSO if sucesso else Resultado.ERRO,
            detalhe=mensagem,
        )
        return render(
            request,
            "provedores/_resultado_teste.html",
            {"provedor": provedor, "sucesso": sucesso, "mensagem": mensagem},
        )


class _ModeloMixin(AdministradorMixin):
    model = ModeloIA
    form_class = ModeloIAForm
    template_name = "provedores/modelo_form.html"
    success_url = reverse_lazy("provedores:lista")

    def registrar(self, verbo: str) -> None:
        registrar(
            Acao.CADASTRO_PROVEDOR,
            request=self.request,
            provedor=self.object.provedor.tipo,
            modelo=self.object.identificador,
            objeto=f"Modelo {verbo}",
        )


class ModeloCreateView(_ModeloMixin, CreateView):
    def dispatch(self, request, *args, **kwargs):
        self.provedor = get_object_or_404(ProvedorIA, pk=kwargs["provedor_pk"])
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        return {**super().get_context_data(**kwargs), "provedor": self.provedor}

    def form_valid(self, form):
        form.instance.provedor = self.provedor
        resposta = super().form_valid(form)
        self.registrar("cadastrado")
        messages.success(self.request, "Modelo cadastrado.")
        return resposta


class ModeloUpdateView(_ModeloMixin, UpdateView):
    def get_context_data(self, **kwargs):
        return {**super().get_context_data(**kwargs), "provedor": self.object.provedor}

    def form_valid(self, form):
        resposta = super().form_valid(form)
        self.registrar("alterado")
        messages.success(self.request, "Modelo atualizado.")
        return resposta
