"""Log de auditoria do FISCO.IA.

Requisitos (CNJ 615/2025 — rastreabilidade; LGPD — necessidade):
- registra apenas METADADOS da operação, nunca conteúdo processual;
- é somente-leitura: registros não podem ser alterados nem excluídos.
"""

from django.conf import settings
from django.db import models


class LogSomenteLeituraError(Exception):
    """Tentativa de alterar ou excluir um registro de auditoria."""


class LogAuditoriaQuerySet(models.QuerySet):
    def update(self, **kwargs):
        raise LogSomenteLeituraError("O log de auditoria é somente-leitura.")

    def delete(self):
        raise LogSomenteLeituraError("O log de auditoria é somente-leitura.")


class Acao(models.TextChoices):
    LOGIN = "login", "Login"
    LOGOUT = "logout", "Logout"
    LOGIN_FALHA = "login_falha", "Tentativa de login malsucedida"
    ANALISE = "analise", "Análise de autos"
    ESCLARECIMENTO = "esclarecimento", "Perguntas de esclarecimento"
    RECUSA_ESCOPO = "recusa_escopo", "Recusa por escopo"
    EXPORTACAO = "exportacao", "Exportação"
    CADASTRO_USUARIO = "cadastro_usuario", "Cadastro/alteração de usuário"
    CADASTRO_PROVEDOR = "cadastro_provedor", "Cadastro/alteração de provedor"
    TESTE_PROVEDOR = "teste_provedor", "Teste de conexão com provedor"
    CADASTRO_AGENTE = "cadastro_agente", "Cadastro/alteração de agente"
    CADASTRO_EMPRESA = "cadastro_empresa", "Cadastro/alteração de empresa"
    EXTRACAO_EXECUCAO = "extracao_execucao", "Extração para a tabela consolidada"
    REVISAO_EXECUCAO = "revisao_execucao", "Revisão manual de execução"


class Resultado(models.TextChoices):
    SUCESSO = "sucesso", "Sucesso"
    ERRO = "erro", "Erro"
    RECUSADO = "recusado", "Recusado"


class LogAuditoria(models.Model):
    criado_em = models.DateTimeField("data e hora", auto_now_add=True, db_index=True)
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="logs_auditoria",
    )
    # Nome registrado no momento da operação (preserva o histórico se o usuário mudar).
    usuario_nome = models.CharField("usuário", max_length=150, blank=True)
    acao = models.CharField("ação", max_length=30, choices=Acao.choices, db_index=True)
    resultado = models.CharField(
        max_length=10, choices=Resultado.choices, default=Resultado.SUCESSO, db_index=True
    )
    numero_processo = models.CharField("número do processo", max_length=30, blank=True)
    agente = models.CharField(max_length=120, blank=True)
    provedor = models.CharField(max_length=30, blank=True)
    modelo = models.CharField(max_length=100, blank=True)
    # Identificação do registro afetado (ex.: "Empresa #3"), nunca conteúdo dos autos.
    objeto = models.CharField(max_length=200, blank=True)
    # Mensagem curta de metadados (ex.: tipo do erro). Limitada por design.
    detalhe = models.CharField(max_length=255, blank=True)
    ip = models.GenericIPAddressField("IP", null=True, blank=True)

    objects = LogAuditoriaQuerySet.as_manager()

    class Meta:
        ordering = ["-criado_em", "-id"]
        verbose_name = "registro de auditoria"
        verbose_name_plural = "log de auditoria"

    def __str__(self) -> str:
        return f"{self.criado_em:%d/%m/%Y %H:%M} — {self.usuario_nome} — {self.get_acao_display()}"

    def save(self, *args, **kwargs):
        if self.pk is not None:
            raise LogSomenteLeituraError("O log de auditoria é somente-leitura.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise LogSomenteLeituraError("O log de auditoria é somente-leitura.")
