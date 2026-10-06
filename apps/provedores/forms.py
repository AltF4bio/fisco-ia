from django import forms

from apps.provedores.models import ModeloIA, ProvedorIA


class ProvedorForm(forms.ModelForm):
    nova_chave = forms.CharField(
        label="Nova chave de API",
        required=False,
        strip=True,
        widget=forms.PasswordInput(render_value=False, attrs={"autocomplete": "off"}),
        help_text="Deixe em branco para manter a chave atual. A chave é armazenada criptografada.",
    )
    remover_chave = forms.BooleanField(label="Remover a chave armazenada", required=False)

    class Meta:
        model = ProvedorIA
        fields = ["ativo"]
        labels = {"ativo": "Provedor ativo (disponível para os agentes)"}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.instance.exige_chave:
            del self.fields["nova_chave"]
            del self.fields["remover_chave"]

    def clean(self):
        dados = super().clean()
        if not self.instance.exige_chave:
            return dados
        if dados.get("nova_chave") and dados.get("remover_chave"):
            raise forms.ValidationError("Informe uma nova chave ou remova a atual, não ambos.")
        tera_chave = bool(dados.get("nova_chave")) or (
            bool(self.instance.chave_cifrada) and not dados.get("remover_chave")
        )
        if dados.get("ativo") and not tera_chave:
            raise forms.ValidationError("Para ativar o provedor, informe a chave de API.")
        return dados

    def save(self, commit: bool = True) -> ProvedorIA:
        provedor = super().save(commit=False)
        if self.cleaned_data.get("remover_chave"):
            provedor.remover_chave()
        elif self.cleaned_data.get("nova_chave"):
            provedor.definir_chave(self.cleaned_data["nova_chave"])
        if commit:
            provedor.save()
        return provedor


class ModeloIAForm(forms.ModelForm):
    class Meta:
        model = ModeloIA
        fields = [
            "identificador",
            "nome_exibicao",
            "limite_contexto_tokens",
            "max_saida_tokens",
            "ativo",
        ]
