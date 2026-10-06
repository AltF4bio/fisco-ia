from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

import anthropic

from apps.provedores.llm.base import (
    LLMAutenticacaoError,
    LLMConexaoError,
    LLMError,
    LLMLimiteError,
    LLMProvider,
    LLMRecusaError,
    LLMResult,
)

INSTRUCAO_JSON = "\n\nResponda exclusivamente com um objeto JSON válido, sem texto adicional."


class AnthropicProvider(LLMProvider):
    """Anthropic (Claude) via Messages API."""

    nome = "anthropic"

    def _cliente(self) -> anthropic.Anthropic:
        return anthropic.Anthropic(api_key=self.api_key, timeout=self.timeout, max_retries=2)

    def generate(self, system_prompt: str, user_content: str, model: str, **opts: Any) -> LLMResult:
        conteudo = user_content + (INSTRUCAO_JSON if opts.get("json") else "")
        with _traduzir_erros():
            resposta = self._cliente().messages.create(
                model=model,
                max_tokens=opts.get("max_tokens", 16000),
                system=system_prompt,
                messages=[{"role": "user", "content": conteudo}],
            )
        if resposta.stop_reason == "refusal":
            raise LLMRecusaError("O modelo da Anthropic recusou a solicitação.")
        texto = "".join(bloco.text for bloco in resposta.content if bloco.type == "text")
        return LLMResult(
            texto=texto,
            provedor=self.nome,
            modelo=model,
            tokens_entrada=resposta.usage.input_tokens,
            tokens_saida=resposta.usage.output_tokens,
        )

    def testar_conexao(self) -> str:
        with _traduzir_erros():
            modelos = list(self._cliente().models.list())
        return f"Conexão estabelecida. {len(modelos)} modelos acessíveis com esta chave."


@contextmanager
def _traduzir_erros() -> Iterator[None]:
    try:
        yield
    except (anthropic.AuthenticationError, anthropic.PermissionDeniedError) as erro:
        raise LLMAutenticacaoError("Chave de API da Anthropic inválida ou sem permissão.") from erro
    except anthropic.RateLimitError as erro:
        raise LLMLimiteError("Limite de uso da Anthropic atingido. Tente mais tarde.") from erro
    except (anthropic.APIConnectionError, anthropic.APITimeoutError) as erro:
        raise LLMConexaoError("Não foi possível conectar à Anthropic.") from erro
    except anthropic.APIError as erro:
        raise LLMError(f"Erro retornado pela Anthropic ({type(erro).__name__}).") from erro
