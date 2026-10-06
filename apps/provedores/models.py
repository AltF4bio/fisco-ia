from __future__ import annotations

from django.db import models

from apps.provedores import cripto


class TipoProvedor(models.TextChoices):
    OPENAI = "openai", "OpenAI (ChatGPT)"
    ANTHROPIC = "anthropic", "Anthropic (Claude)"
    GEMINI = "gemini", "Google (Gemini)"
    MOCK = "mock", "Demonstração (MockProvider)"


class ProvedorIA(models.Model):
    tipo = models.CharField(max_length=20, choices=TipoProvedor.choices, unique=True)
    ativo = models.BooleanField(default=False)
    chave_cifrada = models.TextField(blank=True, editable=False)
    chave_mascarada = models.CharField(max_length=20, blank=True, editable=False)
    ultimo_teste_em = models.DateTimeField(null=True, blank=True)
    ultimo_teste_ok = models.BooleanField(null=True)
    ultimo_teste_mensagem = models.CharField(max_length=255, blank=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["tipo"]
        verbose_name = "provedor de IA"
        verbose_name_plural = "provedores de IA"

    def __str__(self) -> str:
        return self.get_tipo_display()

    @property
    def exige_chave(self) -> bool:
        return self.tipo != TipoProvedor.MOCK

    @property
    def configurado(self) -> bool:
        return not self.exige_chave or bool(self.chave_cifrada)

    @property
    def disponivel(self) -> bool:
        return self.ativo and self.configurado

    def definir_chave(self, chave: str) -> None:
        chave = chave.strip()
        self.chave_cifrada = cripto.cifrar(chave)
        self.chave_mascarada = cripto.mascarar(chave)

    def remover_chave(self) -> None:
        self.chave_cifrada = ""
        self.chave_mascarada = ""
        self.ativo = False

    def obter_chave(self) -> str | None:
        return cripto.decifrar(self.chave_cifrada) if self.chave_cifrada else None


class ModeloIAQuerySet(models.QuerySet):
    def disponiveis(self) -> ModeloIAQuerySet:
        """Modelos ativos de provedores ativos e configurados."""
        return (
            self.filter(ativo=True, provedor__ativo=True)
            .exclude(provedor__chave_cifrada="", provedor__tipo__in=_TIPOS_COM_CHAVE)
            .select_related("provedor")
        )


_TIPOS_COM_CHAVE = [t for t in TipoProvedor.values if t != TipoProvedor.MOCK]


class ModeloIA(models.Model):
    provedor = models.ForeignKey(ProvedorIA, on_delete=models.CASCADE, related_name="modelos")
    identificador = models.CharField(
        max_length=100, help_text="Identificador exato do modelo na API do provedor."
    )
    nome_exibicao = models.CharField("nome de exibição", max_length=100)
    limite_contexto_tokens = models.PositiveIntegerField(
        "limite de contexto (tokens)",
        help_text="Acima deste tamanho, os autos são divididos em blocos (map-reduce).",
    )
    max_saida_tokens = models.PositiveIntegerField("máximo de tokens de saída", default=16000)
    ativo = models.BooleanField(default=True)

    objects = ModeloIAQuerySet.as_manager()

    class Meta:
        ordering = ["provedor__tipo", "nome_exibicao"]
        constraints = [
            models.UniqueConstraint(
                fields=["provedor", "identificador"], name="modelo_unico_por_provedor"
            )
        ]
        verbose_name = "modelo de IA"
        verbose_name_plural = "modelos de IA"

    def __str__(self) -> str:
        return f"{self.provedor.get_tipo_display()} · {self.nome_exibicao}"
