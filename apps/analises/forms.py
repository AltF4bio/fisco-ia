from django import forms
from django.conf import settings
from django.core.validators import RegexValidator
from django.db.models import Q

from apps.agentes.models import Agente
from apps.provedores.models import ModeloIA

validar_numero_cnj = RegexValidator(
    r"^\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}$",
    "Use o formato CNJ: NNNNNNN-DD.AAAA.J.TR.OOOO.",
)


class CampoPDF(forms.FileField):
    """Aceita somente PDF dentro do tamanho máximo configurado."""

    def __init__(self, **kwargs):
        kwargs.setdefault("widget", forms.ClearableFileInput(attrs={"accept": "application/pdf"}))
        super().__init__(**kwargs)

    def clean(self, *args, **kwargs):
        arquivo = super().clean(*args, **kwargs)
        if arquivo is None:
            return arquivo
        limite = settings.FISCO_PDF_MAX_MB * 1024 * 1024
        if arquivo.size > limite:
            raise forms.ValidationError(f"O arquivo excede {settings.FISCO_PDF_MAX_MB} MB.")
        cabecalho = arquivo.read(5)
        arquivo.seek(0)
        if not arquivo.name.lower().endswith(".pdf") or cabecalho != b"%PDF-":
            raise forms.ValidationError("Envie um arquivo PDF válido.")
        return arquivo


def agentes_executaveis():
    """Agentes ativos cujo modelo pode ser executado agora."""
    qs = Agente.objects.selecionaveis()
    if settings.FISCO_MODO_DEMO:
        return qs
    return qs.filter(Q(modelo__in=ModeloIA.objects.disponiveis()))


class NovaAnaliseForm(forms.Form):
    arquivo = CampoPDF(
        label="PDF dos autos",
        help_text="Arquivo com todas as movimentações do processo. O PDF e o texto extraído são "
        "descartados após a análise.",
    )
    agente = forms.ModelChoiceField(
        queryset=Agente.objects.none(),
        label="Agente",
        empty_label="Selecione o agente…",
    )
    numero_processo = forms.CharField(
        label="Número do processo (opcional)",
        required=False,
        validators=[validar_numero_cnj],
        help_text="Se não informado, o sistema tenta identificá-lo no próprio documento.",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["agente"].queryset = agentes_executaveis()


class RespostasForm(forms.Form):
    """Campos dinâmicos: uma resposta por pergunta de esclarecimento."""

    def __init__(self, *args, perguntas: list[dict], **kwargs):
        super().__init__(*args, **kwargs)
        self.perguntas = perguntas
        for pergunta in perguntas:
            self.fields[pergunta["id"]] = forms.CharField(
                label=pergunta["pergunta"],
                required=False,
                max_length=2000,
                widget=forms.Textarea(attrs={"rows": 3}),
                help_text=pergunta.get("referencia", ""),
            )
