from datetime import datetime, time

from django import forms
from django.utils import timezone
from django.views.generic import ListView

from apps.auditoria.models import Acao, LogAuditoria, Resultado
from apps.core.permissoes import AdministradorMixin


class FiltroAuditoriaForm(forms.Form):
    usuario = forms.CharField(required=False, label="Usuário")
    acao = forms.ChoiceField(required=False, label="Ação", choices=[("", "Todas"), *Acao.choices])
    resultado = forms.ChoiceField(
        required=False, label="Resultado", choices=[("", "Todos"), *Resultado.choices]
    )
    numero_processo = forms.CharField(required=False, label="Número do processo")
    inicio = forms.DateField(
        required=False, label="De", widget=forms.DateInput(attrs={"type": "date"})
    )
    fim = forms.DateField(
        required=False, label="Até", widget=forms.DateInput(attrs={"type": "date"})
    )


class AuditoriaListView(AdministradorMixin, ListView):
    """Consulta somente-leitura do log de auditoria (sem edição ou exclusão)."""

    template_name = "auditoria/lista.html"
    context_object_name = "registros"
    paginate_by = 50

    def get_queryset(self):
        qs = LogAuditoria.objects.all()
        self.form = FiltroAuditoriaForm(self.request.GET or None)
        if self.form.is_valid():
            dados = self.form.cleaned_data
            if dados["usuario"]:
                qs = qs.filter(usuario_nome__icontains=dados["usuario"])
            if dados["acao"]:
                qs = qs.filter(acao=dados["acao"])
            if dados["resultado"]:
                qs = qs.filter(resultado=dados["resultado"])
            if dados["numero_processo"]:
                qs = qs.filter(numero_processo__icontains=dados["numero_processo"])
            if dados["inicio"]:
                inicio = timezone.make_aware(datetime.combine(dados["inicio"], time.min))
                qs = qs.filter(criado_em__gte=inicio)
            if dados["fim"]:
                qs = qs.filter(
                    criado_em__lte=timezone.make_aware(datetime.combine(dados["fim"], time.max))
                )
        return qs

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        consulta = self.request.GET.copy()
        consulta.pop("page", None)
        contexto.update(form=self.form, consulta=consulta.urlencode())
        return contexto
