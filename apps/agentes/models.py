from django.db import models

from apps.provedores.models import ModeloIA


class AgenteQuerySet(models.QuerySet):
    def selecionaveis(self):
        """Agentes que o procurador pode escolher na tela de análise."""
        return self.filter(ativo=True, interno=False).select_related("modelo__provedor")


class Agente(models.Model):
    nome = models.CharField(max_length=120)
    slug = models.SlugField(
        max_length=60, unique=True, help_text="Identificador estável do agente."
    )
    descricao = models.TextField("descrição")
    prompt = models.TextField(
        "prompt de instruções",
        help_text="Instruções enviadas ao modelo como prompt de sistema.",
    )
    modelo = models.ForeignKey(
        ModeloIA,
        on_delete=models.PROTECT,
        related_name="agentes",
        help_text="Provedor e modelo que executam o agente. Apenas provedores ativos são listados.",
    )
    modo_interativo = models.BooleanField(
        "modo interativo de esclarecimento",
        default=False,
        help_text="Antes de concluir, o modelo identifica lacunas e faz perguntas ao procurador.",
    )
    ativo = models.BooleanField(default=True)
    interno = models.BooleanField(
        default=False,
        editable=False,
        help_text="Agente usado internamente pelo sistema (não aparece na tela de análise).",
    )
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    objects = AgenteQuerySet.as_manager()

    class Meta:
        ordering = ["interno", "nome"]

    def __str__(self) -> str:
        return self.nome
