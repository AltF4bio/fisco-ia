from django import forms
from django.db.models import Q

from apps.agentes.models import Agente
from apps.provedores.models import ModeloIA


class AgenteForm(forms.ModelForm):
    class Meta:
        model = Agente
        fields = ["nome", "slug", "descricao", "prompt", "modelo", "modo_interativo", "ativo"]
        widgets = {
            "descricao": forms.Textarea(attrs={"rows": 2}),
            "prompt": forms.Textarea(attrs={"rows": 18, "class": "font-monospace"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Somente modelos de provedores configurados e ativos (mantém o atual, se houver).
        disponiveis = ModeloIA.objects.disponiveis().values("pk")
        filtro = Q(pk__in=disponiveis)
        if self.instance.pk:
            filtro |= Q(pk=self.instance.modelo_id)
        self.fields["modelo"].queryset = ModeloIA.objects.filter(filtro).select_related("provedor")
        self.fields["modelo"].label = "Provedor / modelo"
        if self.instance.interno:
            del self.fields["modo_interativo"]
            self.fields["slug"].disabled = True

    def clean_modelo(self):
        modelo = self.cleaned_data["modelo"]
        if not modelo.ativo or not modelo.provedor.disponivel:
            raise forms.ValidationError(
                "O modelo escolhido pertence a um provedor inativo ou sem chave configurada."
            )
        return modelo
