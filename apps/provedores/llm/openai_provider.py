from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

import openai

from apps.provedores.llm.base import (
    LLMAutenticacaoError,
    LLMConexaoError,
    LLMError,
    LLMLimiteError,
    LLMProvider,
    LLMResult,
)


class OpenAIProvider(LLMProvider):
    """OpenAI (ChatGPT) via Responses API."""

    nome = "openai"

    def _cliente(self) -> openai.OpenAI:
        return openai.OpenAI(api_key=self.api_key, timeout=self.timeout, max_retries=2)

    def generate(self, system_prompt: str, user_content: str, model: str, **opts: Any) -> LLMResult:
        parametros: dict[str, Any] = {
            "model": model,
            "instructions": system_prompt,
            "input": user_content,
            "max_output_tokens": opts.get("max_tokens", 16000),
            "store": False,  # não reter a conversa no provedor
        }
        if opts.get("json"):
            parametros["text"] = {"format": {"type": "json_object"}}
        with _traduzir_erros():
            resposta = self._cliente().responses.create(**parametros)
        uso = getattr(resposta, "usage", None)
        return LLMResult(
            texto=resposta.output_text or "",
            provedor=self.nome,
            modelo=model,
            tokens_entrada=getattr(uso, "input_tokens", None),
            tokens_saida=getattr(uso, "output_tokens", None),
        )

    def testar_conexao(self) -> str:
        with _traduzir_erros():
            modelos = list(self._cliente().models.list())
        return f"Conexão estabelecida. {len(modelos)} modelos acessíveis com esta chave."


@contextmanager
def _traduzir_erros() -> Iterator[None]:
    try:
        yield
    except (openai.AuthenticationError, openai.PermissionDeniedError) as erro:
        raise LLMAutenticacaoError("Chave de API da OpenAI inválida ou sem permissão.") from erro
    except openai.RateLimitError as erro:
        raise LLMLimiteError("Limite de uso da OpenAI atingido. Tente mais tarde.") from erro
    except (openai.APIConnectionError, openai.APITimeoutError) as erro:
        raise LLMConexaoError("Não foi possível conectar à OpenAI.") from erro
    except openai.APIError as erro:
        raise LLMError(f"Erro retornado pela OpenAI ({type(erro).__name__}).") from erro
