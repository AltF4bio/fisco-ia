"""Armazenamento transitório do fluxo de análise (LGPD: finalidade e necessidade).

- O texto dos autos só é mantido entre a etapa de perguntas e a análise final, em
  arquivo temporário fora do MEDIA_ROOT, e é apagado logo após a análise (ou ao
  cancelar). Arquivos órfãos são removidos por expiração.
- O resultado da análise fica apenas na sessão do usuário (cache com expiração,
  nunca no banco de dados), para leitura e exportação.
"""

from __future__ import annotations

import contextlib
import time
import uuid
from pathlib import Path
from typing import Any

from django.conf import settings
from django.contrib.sessions.backends.base import SessionBase
from django.utils import timezone

CHAVE_PENDENTE = "analise_pendente"
CHAVE_RESULTADOS = "analises"
MAXIMO_RESULTADOS = 10


# --- arquivos temporários -------------------------------------------------------


def diretorio_temporario() -> Path:
    diretorio = Path(settings.FISCO_TEMP_DIR)
    diretorio.mkdir(parents=True, exist_ok=True)
    return diretorio


def _caminho(token: str) -> Path:
    # O token é sempre um UUID gerado pelo sistema; a validação impede path traversal.
    return diretorio_temporario() / f"{uuid.UUID(token).hex}.txt"


def guardar_texto_temporario(texto: str) -> str:
    token = uuid.uuid4().hex
    _caminho(token).write_text(texto, encoding="utf-8")
    return token


def ler_texto_temporario(token: str) -> str | None:
    try:
        return _caminho(token).read_text(encoding="utf-8")
    except (FileNotFoundError, ValueError):
        return None


def descartar_texto_temporario(token: str | None) -> None:
    if token:
        with contextlib.suppress(ValueError):
            _caminho(token).unlink(missing_ok=True)


def limpar_temporarios_expirados(idade_maxima_segundos: int | None = None) -> int:
    """Remove textos temporários mais antigos que a duração da sessão."""
    idade = idade_maxima_segundos or settings.SESSION_COOKIE_AGE
    limite = time.time() - idade
    removidos = 0
    for arquivo in diretorio_temporario().glob("*.txt"):
        if arquivo.stat().st_mtime < limite:
            arquivo.unlink(missing_ok=True)
            removidos += 1
    return removidos


# --- análise pendente (aguardando respostas do procurador) ----------------------


def iniciar_pendente(session: SessionBase, texto: str, dados: dict[str, Any]) -> None:
    cancelar_pendente(session)
    session[CHAVE_PENDENTE] = {**dados, "token": guardar_texto_temporario(texto)}


def obter_pendente(session: SessionBase) -> dict[str, Any] | None:
    return session.get(CHAVE_PENDENTE)


def cancelar_pendente(session: SessionBase) -> None:
    pendente = session.pop(CHAVE_PENDENTE, None)
    if pendente:
        descartar_texto_temporario(pendente.get("token"))


# --- resultados -------------------------------------------------------------------


def guardar_resultado(session: SessionBase, dados: dict[str, Any]) -> str:
    identificador = uuid.uuid4().hex
    resultados = dict(session.get(CHAVE_RESULTADOS, {}))
    resultados[identificador] = {**dados, "criado_em": timezone.now().isoformat()}
    # Mantém apenas os resultados mais recentes da sessão.
    mais_recentes = sorted(resultados.items(), key=lambda i: i[1]["criado_em"])[-MAXIMO_RESULTADOS:]
    session[CHAVE_RESULTADOS] = dict(mais_recentes)
    return identificador


def obter_resultado(session: SessionBase, identificador: str) -> dict[str, Any] | None:
    return session.get(CHAVE_RESULTADOS, {}).get(identificador)


def listar_resultados(session: SessionBase) -> list[tuple[str, dict[str, Any]]]:
    resultados = session.get(CHAVE_RESULTADOS, {})
    return sorted(resultados.items(), key=lambda i: i[1]["criado_em"], reverse=True)
