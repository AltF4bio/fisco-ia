"""Camada de integração com provedores de IA generativa."""

from apps.provedores.llm.base import (
    LLMAutenticacaoError,
    LLMConexaoError,
    LLMError,
    LLMLimiteError,
    LLMProvider,
    LLMRecusaError,
    LLMResult,
)
from apps.provedores.llm.factory import PROVEDORES, get_provider
from apps.provedores.llm.tarefas import Tarefa

__all__ = [
    "PROVEDORES",
    "LLMAutenticacaoError",
    "LLMConexaoError",
    "LLMError",
    "LLMLimiteError",
    "LLMProvider",
    "LLMRecusaError",
    "LLMResult",
    "Tarefa",
    "get_provider",
]
