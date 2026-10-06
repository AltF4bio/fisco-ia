"""Divisão dos autos em blocos quando excedem o contexto do modelo (map-reduce)."""

from __future__ import annotations

import math
import re

from apps.provedores.models import ModeloIA

# Estimativa conservadora para textos em português (caracteres por token).
CARACTERES_POR_TOKEN = 3.5
MARGEM_SEGURANCA = 0.9
_SEPARADOR_FOLHA = re.compile(r"(?=--- \[fl\. \d+\] ---)")


def estimar_tokens(texto: str) -> int:
    return math.ceil(len(texto) / CARACTERES_POR_TOKEN)


def orcamento_entrada(modelo: ModeloIA, system_prompt: str) -> int:
    """Tokens disponíveis para os autos, descontando prompt, saída e margem."""
    disponivel = (
        modelo.limite_contexto_tokens * MARGEM_SEGURANCA
        - modelo.max_saida_tokens
        - estimar_tokens(system_prompt)
    )
    return max(500, int(disponivel))


def cabe_no_contexto(texto: str, orcamento_tokens: int) -> bool:
    return estimar_tokens(texto) <= orcamento_tokens


def dividir(texto: str, orcamento_tokens: int) -> list[str]:
    """Agrupa folhas inteiras em blocos; folhas maiores que o orçamento são fatiadas."""
    limite = int(orcamento_tokens * CARACTERES_POR_TOKEN)
    pecas: list[str] = []
    for folha in filter(None, _SEPARADOR_FOLHA.split(texto)):
        if len(folha) <= limite:
            pecas.append(folha)
        else:
            pecas += [folha[i : i + limite] for i in range(0, len(folha), limite)]

    blocos: list[str] = []
    atual = ""
    for peca in pecas:
        if atual and len(atual) + len(peca) > limite:
            blocos.append(atual)
            atual = ""
        atual += peca
    if atual:
        blocos.append(atual)
    return blocos
