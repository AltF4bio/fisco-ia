"""Contrato comum da camada de integração com modelos de linguagem.

Os módulos de aplicação dependem apenas desta interface. Trocar o provedor ou o
modelo de um agente não exige alteração em nenhum outro módulo.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class LLMResult:
    """Resposta padronizada de qualquer provedor."""

    texto: str
    provedor: str
    modelo: str
    tokens_entrada: int | None = None
    tokens_saida: int | None = None


class LLMError(Exception):
    """Falha ao comunicar com o provedor. A mensagem é segura para exibir ao usuário."""


class LLMAutenticacaoError(LLMError):
    pass


class LLMConexaoError(LLMError):
    pass


class LLMLimiteError(LLMError):
    pass


class LLMRecusaError(LLMError):
    """O modelo recusou a solicitação (ex.: filtros de segurança do provedor)."""


class LLMProvider(ABC):
    """Interface abstrata de um provedor de IA generativa."""

    nome: str = ""

    def __init__(self, api_key: str | None = None, timeout: float = 180) -> None:
        self.api_key = api_key
        self.timeout = timeout

    @abstractmethod
    def generate(
        self,
        system_prompt: str,
        user_content: str,
        model: str,
        **opts: Any,
    ) -> LLMResult:
        """Gera uma resposta.

        Opções reconhecidas:
            max_tokens (int): limite de tokens de saída.
            json (bool): solicita resposta em JSON (quando o provedor suporta).
        Opções desconhecidas são ignoradas pelos provedores reais.
        """

    @abstractmethod
    def testar_conexao(self) -> str:
        """Verifica credenciais e conectividade sem consumir tokens de geração.

        Retorna uma mensagem descritiva; levanta ``LLMError`` em caso de falha.
        """
