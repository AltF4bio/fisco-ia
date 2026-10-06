from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

from google import genai
from google.genai import errors, types

from apps.provedores.llm.base import (
    LLMAutenticacaoError,
    LLMConexaoError,
    LLMError,
    LLMLimiteError,
    LLMProvider,
    LLMRecusaError,
    LLMResult,
)


class GeminiProvider(LLMProvider):
    """Google Gemini via SDK google-genai."""

    nome = "gemini"

    def _cliente(self) -> genai.Client:
        return genai.Client(
            api_key=self.api_key,
            http_options=types.HttpOptions(timeout=int(self.timeout * 1000)),
        )

    def generate(self, system_prompt: str, user_content: str, model: str, **opts: Any) -> LLMResult:
        config = types.GenerateContentConfig(
            system_instruction=system_prompt,
            max_output_tokens=opts.get("max_tokens", 16000),
            response_mime_type="application/json" if opts.get("json") else None,
        )
        with _traduzir_erros():
            resposta = self._cliente().models.generate_content(
                model=model, contents=user_content, config=config
            )
        texto = resposta.text
        if texto is None:
            raise LLMRecusaError("O modelo Gemini não retornou conteúdo (possível bloqueio).")
        uso = resposta.usage_metadata
        return LLMResult(
            texto=texto,
            provedor=self.nome,
            modelo=model,
            tokens_entrada=getattr(uso, "prompt_token_count", None),
            tokens_saida=getattr(uso, "candidates_token_count", None),
        )

    def testar_conexao(self) -> str:
        with _traduzir_erros():
            modelos = list(self._cliente().models.list())
        return f"Conexão estabelecida. {len(modelos)} modelos acessíveis com esta chave."


@contextmanager
def _traduzir_erros() -> Iterator[None]:
    try:
        yield
    except errors.ClientError as erro:
        codigo = getattr(erro, "code", None)
        if codigo in (401, 403) or (codigo == 400 and "API key" in str(erro)):
            raise LLMAutenticacaoError(
                "Chave de API do Google inválida ou sem permissão."
            ) from erro
        if codigo == 429:
            raise LLMLimiteError("Limite de uso do Gemini atingido. Tente mais tarde.") from erro
        raise LLMError(f"Erro retornado pelo Gemini (HTTP {codigo}).") from erro
    except errors.APIError as erro:
        raise LLMError("Erro no serviço do Gemini.") from erro
    except (OSError, TimeoutError) as erro:
        raise LLMConexaoError("Não foi possível conectar ao Gemini.") from erro
