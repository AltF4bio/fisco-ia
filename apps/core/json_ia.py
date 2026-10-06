"""Leitura tolerante de JSON devolvido por modelos de linguagem."""

from __future__ import annotations

import json
import re
from typing import Any

_CERCA = re.compile(r"```(?:json)?\s*(.*?)```", re.DOTALL | re.IGNORECASE)


class JSONInvalidoError(ValueError):
    pass


def ler_objeto_json(texto: str) -> dict[str, Any]:
    """Extrai o primeiro objeto JSON da resposta (aceita blocos ```json ... ```)."""
    candidato = texto.strip()
    cerca = _CERCA.search(candidato)
    if cerca:
        candidato = cerca.group(1).strip()
    inicio, fim = candidato.find("{"), candidato.rfind("}")
    if inicio == -1 or fim <= inicio:
        raise JSONInvalidoError("A resposta do modelo não contém um objeto JSON.")
    try:
        dados = json.loads(candidato[inicio : fim + 1])
    except json.JSONDecodeError as erro:
        raise JSONInvalidoError("A resposta do modelo contém JSON malformado.") from erro
    if not isinstance(dados, dict):
        raise JSONInvalidoError("A resposta do modelo não é um objeto JSON.")
    return dados
