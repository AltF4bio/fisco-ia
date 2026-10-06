"""Cadastro inicial dos agentes do TCC."""

from __future__ import annotations

from apps.agentes.models import Agente
from apps.agentes.prompts import AGENTE_EXTRACAO, AGENTES
from apps.provedores.models import ModeloIA, TipoProvedor


def modelo_padrao() -> ModeloIA:
    """Primeiro modelo disponível de um provedor real; na falta, o de demonstração."""
    real = ModeloIA.objects.disponiveis().exclude(provedor__tipo=TipoProvedor.MOCK).first()
    if real is not None:
        return real
    return ModeloIA.objects.get(provedor__tipo=TipoProvedor.MOCK, identificador="mock-fisco")


def semear_agentes(
    modelo: ModeloIA | None = None, *, atualizar_prompts: bool = False
) -> list[tuple[Agente, bool]]:
    """Cria (ou atualiza) os cinco agentes do TCC e o agente interno de extração.

    O modelo de agentes já existentes só é alterado quando ``modelo`` é informado,
    preservando escolhas feitas pelo administrador.
    """
    resultado = []
    for dados in [*AGENTES, AGENTE_EXTRACAO]:
        dados = dict(dados)
        slug = dados.pop("slug")
        agente = Agente.objects.filter(slug=slug).first()
        if agente is None:
            agente = Agente.objects.create(slug=slug, modelo=modelo or modelo_padrao(), **dados)
            resultado.append((agente, True))
            continue
        if atualizar_prompts:
            for campo, valor in dados.items():
                setattr(agente, campo, valor)
        if modelo is not None:
            agente.modelo = modelo
        agente.save()
        resultado.append((agente, False))
    return resultado
