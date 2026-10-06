from decimal import Decimal

from django import forms

from apps.analises.forms import CampoPDF, validar_numero_cnj
from apps.empresas import cnpj
from apps.empresas.models import Empresa, ExecucaoFiscal

MAXIMO_ARQUIVOS = 10


class EmpresaForm(forms.ModelForm):
    cnpj = forms.CharField(
        label="CNPJ",
        max_length=18,
        help_text="Aceita o formato numérico e o CNPJ alfanumérico (IN RFB 2.229/2024).",
    )

    class Meta:
        model = Empresa
        fields = ["razao_social", "cnpj", "observacoes"]
        widgets = {"observacoes": forms.Textarea(attrs={"rows": 3})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            self.initial["cnpj"] = self.instance.cnpj_formatado

    def clean_cnpj(self) -> str:
        valor = cnpj.normalizar(self.cleaned_data["cnpj"])
        cnpj.validar(valor)
        if Empresa.objects.exclude(pk=self.instance.pk).filter(cnpj=valor).exists():
            raise forms.ValidationError("Já existe empresa cadastrada com este CNPJ.")
        return valor


class MultiplosArquivosInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class CampoMultiplosPDFs(CampoPDF):
    def __init__(self, **kwargs):
        kwargs.setdefault(
            "widget", MultiplosArquivosInput(attrs={"accept": "application/pdf", "multiple": True})
        )
        super().__init__(**kwargs)

    def clean(self, data, initial=None):
        arquivos = data if isinstance(data, list | tuple) else [data]
        if len(arquivos) > MAXIMO_ARQUIVOS:
            raise forms.ValidationError(f"Envie no máximo {MAXIMO_ARQUIVOS} arquivos por vez.")
        return [super(CampoMultiplosPDFs, self).clean(a, initial) for a in arquivos]


class EnvioExecucoesForm(forms.Form):
    arquivos = CampoMultiplosPDFs(
        label="PDFs das execuções fiscais",
        help_text="Um PDF por processo. Os arquivos e o texto extraído são descartados após o "
        "processamento; apenas os campos da tabela consolidada são armazenados.",
    )


def _linhas(texto: str) -> list[str]:
    return [linha.strip() for linha in texto.splitlines() if linha.strip()]


class ExecucaoRevisaoForm(forms.ModelForm):
    """Correção manual: os campos alterados passam a prevalecer sobre a extração da IA."""

    cdas = forms.CharField(
        label="CDA(s)", required=False, widget=forms.Textarea(attrs={"rows": 2}),
        help_text="Uma por linha.",
    )  # fmt: skip
    bens_penhorados = forms.CharField(
        label="Bens penhorados", required=False, widget=forms.Textarea(attrs={"rows": 3}),
        help_text="Um por linha.",
    )  # fmt: skip
    apropriacoes = forms.CharField(
        label="Apropriações", required=False, widget=forms.Textarea(attrs={"rows": 3}),
        help_text="Uma por linha, no formato: descrição | protocolo SEFA.",
    )  # fmt: skip
    teses_defesa = forms.CharField(
        label="Teses de defesa", required=False, widget=forms.Textarea(attrs={"rows": 2}),
        help_text="Uma por linha.",
    )  # fmt: skip

    class Meta:
        model = ExecucaoFiscal
        fields = [
            "numero_processo",
            "cdas",
            "valor_executado",
            "bens_penhorados",
            "apropriacoes",
            "teses_defesa",
            "situacao",
            "situacao_detalhe",
            "acao_imediata",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["numero_processo"].validators.append(validar_numero_cnj)
        execucao = self.instance
        self.initial.update(
            cdas="\n".join(execucao.cdas),
            bens_penhorados="\n".join(execucao.bens_penhorados),
            teses_defesa="\n".join(execucao.teses_defesa),
            apropriacoes="\n".join(
                f"{a.get('descricao', '')} | {a.get('protocolo_sefa', '')}".strip(" |")
                for a in execucao.apropriacoes
            ),
        )

    def clean_cdas(self):
        return _linhas(self.cleaned_data["cdas"])

    def clean_bens_penhorados(self):
        return _linhas(self.cleaned_data["bens_penhorados"])

    def clean_teses_defesa(self):
        return _linhas(self.cleaned_data["teses_defesa"])

    def clean_apropriacoes(self):
        itens = []
        for linha in _linhas(self.cleaned_data["apropriacoes"]):
            descricao, _, protocolo = linha.partition("|")
            itens.append({"descricao": descricao.strip(), "protocolo_sefa": protocolo.strip()})
        return itens

    def campos_alterados(self, original: ExecucaoFiscal) -> list[str]:
        alterados = []
        for campo in self.Meta.fields:
            novo, antigo = self.cleaned_data[campo], getattr(original, campo)
            if isinstance(novo, Decimal) or isinstance(antigo, Decimal):
                igual = (novo or Decimal(0)) == (antigo or Decimal(0)) and (novo is None) == (
                    antigo is None
                )
            else:
                igual = novo == antigo
            if not igual:
                alterados.append(campo)
        return alterados
