"""Fábrica de provedores: o único ponto que conhece as implementações concretas."""

from __future__ import annotations

from apps.provedores.llm.anthropic_provider import AnthropicProvider
from apps.provedores.llm.base import LLMProvider
from apps.provedores.llm.gemini_provider import GeminiProvider
from apps.provedores.llm.mock_provider import MockProvider
from apps.provedores.llm.openai_provider import OpenAIProvider

PROVEDORES: dict[str, type[LLMProvider]] = {
    OpenAIProvider.nome: OpenAIProvider,
    AnthropicProvider.nome: AnthropicProvider,
    GeminiProvider.nome: GeminiProvider,
    MockProvider.nome: MockProvider,
}


def get_provider(nome: str, api_key: str | None = None, timeout: float = 180) -> LLMProvider:
    """Instancia o provedor pelo nome (``openai``, ``anthropic``, ``gemini`` ou ``mock``)."""
    try:
        classe = PROVEDORES[nome]
    except KeyError as erro:
        raise ValueError(f"Provedor de IA desconhecido: {nome!r}") from erro
    return classe(api_key=api_key, timeout=timeout)
