from django.conf import settings
from django.db import models

from apps.empresas import cnpj


class Empresa(models.Model):
    """Empresa contribuinte executada pelo Estado."""

    razao_social = models.CharField("razão social", max_length=200)
    cnpj = models.CharField("CNPJ", max_length=14, unique=True, validators=[cnpj.validar])
    observacoes = models.TextField("observações", blank=True)
    criado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, editable=False
    )
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["razao_social"]

    def __str__(self) -> str:
        return self.razao_social

    @property
    def cnpj_formatado(self) -> str:
        return cnpj.formatar(self.cnpj)


class Situacao(models.TextChoices):
    EM_ANDAMENTO = "em_andamento", "Em andamento"
    CUMPRIMENTO = "cumprimento", "Em fase de cumprimento"
    SUSPENSO = "suspenso", "Suspenso"
    AGUARDANDO_MANIFESTACAO = "aguardando_manifestacao", "Aguardando manifestação"
    RECURSO_PENDENTE = "recurso_pendente", "Com recurso pendente"
    ENCERRADO = "encerrado", "Encerrado"


class ExecucaoFiscal(models.Model):
    """Linha da tabela consolidada (chave: número do processo).

    Guarda somente os campos previstos na especificação. Campos corrigidos pelo
    procurador ficam em ``campos_revisados`` e não são sobrescritos pela IA.
    """

    CAMPOS_EXTRAIDOS = (
        "numero_processo",
        "cdas",
        "valor_executado",
        "bens_penhorados",
        "apropriacoes",
        "teses_defesa",
        "situacao",
        "situacao_detalhe",
        "acao_imediata",
    )

    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name="execucoes")
    numero_processo = models.CharField("número do processo", max_length=30, unique=True)
    cdas = models.JSONField("CDA(s)", default=list, blank=True)
    valor_executado = models.DecimalField(
        "valor executado", max_digits=15, decimal_places=2, null=True, blank=True
    )
    bens_penhorados = models.JSONField("bens penhorados", default=list, blank=True)
    apropriacoes = models.JSONField(
        "apropriações", default=list, blank=True, help_text="Itens com descrição e protocolo SEFA."
    )
    teses_defesa = models.JSONField("teses de defesa", default=list, blank=True)
    situacao = models.CharField(
        "situação processual",
        max_length=30,
        choices=Situacao.choices,
        default=Situacao.EM_ANDAMENTO,
        db_index=True,
    )
    situacao_detalhe = models.CharField("detalhe da situação", max_length=300, blank=True)
    acao_imediata = models.BooleanField("demanda ação imediata", default=False, db_index=True)
    revisado_manualmente = models.BooleanField("revisado pelo procurador", default=False)
    campos_revisados = models.JSONField(default=list, blank=True, editable=False)
    criado_em = models.DateTimeField(auto_now_add=True)
    ultima_atualizacao = models.DateTimeField("última atualização", auto_now=True)

    class Meta:
        ordering = ["-acao_imediata", "numero_processo"]
        verbose_name = "execução fiscal"
        verbose_name_plural = "execuções fiscais"

    def __str__(self) -> str:
        return self.numero_processo

    def foi_revisado(self, campo: str) -> bool:
        return campo in self.campos_revisados
