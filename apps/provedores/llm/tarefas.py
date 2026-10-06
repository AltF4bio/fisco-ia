from enum import StrEnum


class Tarefa(StrEnum):
    """Natureza de cada chamada ao modelo.

    Enviada como opção ``tarefa`` em ``LLMProvider.generate``. Os provedores reais
    a ignoram (o comportamento vem do prompt); o MockProvider a usa para escolher
    a resposta de exemplo adequada.
    """

    ESCOPO = "escopo"
    PERGUNTAS = "perguntas"
    ANALISE = "analise"
    PARCIAL = "parcial"
    CONSOLIDACAO = "consolidacao"
    EXTRACAO = "extracao"
