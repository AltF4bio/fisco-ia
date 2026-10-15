"""Serviços de acesso aos modelos de IA usados pelos demais módulos.

Os módulos de aplicação chamam ``gerar(modelo, ...)`` passando o ``ModeloIA`` do
agente; a escolha do provedor concreto acontece somente aqui e na fábrica.
"""

from __future__ import annotations

import logging
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

from django.conf import settings
from django.utils import timezone

from apps.provedores.cripto import ChaveIndisponivelError
from apps.provedores.llm import LLMError, LLMProvider, LLMResult, get_provider
from apps.provedores.models import ModeloIA, ProvedorIA, TipoProvedor

logger = logging.getLogger(__name__)


def modo_demo() -> bool:
    return bool(settings.FISCO_MODO_DEMO)


def instanciar(provedor: ProvedorIA) -> LLMProvider:
    """Cria o cliente do provedor com a chave decifrada (somente em memória)."""
    try:
        chave = provedor.obter_chave()
    except ChaveIndisponivelError as erro:
        raise LLMError(str(erro)) from erro
    if provedor.exige_chave and not chave:
        raise LLMError(f"O provedor {provedor} não tem chave de API configurada.")
    return get_provider(provedor.tipo, api_key=chave, timeout=settings.FISCO_LLM_TIMEOUT)


def provedor_para(modelo: ModeloIA) -> LLMProvider:
    """Provedor que executará o modelo.

    Em modo demonstração (``FISCO_MODO_DEMO``), todas as chamadas são atendidas pelo
    MockProvider, garantindo que nenhuma chave real seja usada.
    """
    if modo_demo():
        return get_provider(TipoProvedor.MOCK)
    if not modelo.provedor.disponivel:
        raise LLMError(f"O provedor {modelo.provedor} está inativo ou sem chave configurada.")
    return instanciar(modelo.provedor)


@contextmanager
def _falhas_inesperadas_como_llm_error(provedor: str) -> Iterator[None]:
    """Converte falhas não previstas do SDK em ``LLMError``, para que o usuário
    receba uma mensagem na tela em vez de um erro interno do servidor."""
    try:
        yield
    except LLMError:
        raise
    except Exception as erro:
        logger.exception("Falha inesperada no provedor %s", provedor)
        raise LLMError(
            f"Falha inesperada ao comunicar com o provedor ({type(erro).__name__})."
        ) from erro


def gerar(modelo: ModeloIA, system_prompt: str, user_content: str, **opts: Any) -> LLMResult:
    opts.setdefault("max_tokens", modelo.max_saida_tokens)
    provedor = provedor_para(modelo)
    with _falhas_inesperadas_como_llm_error(provedor.nome):
        return provedor.generate(system_prompt, user_content, modelo.identificador, **opts)


def testar_conexao(provedor: ProvedorIA) -> tuple[bool, str]:
    """Testa as credenciais do provedor e registra o resultado no cadastro."""
    try:
        with _falhas_inesperadas_como_llm_error(provedor.tipo):
            mensagem = instanciar(provedor).testar_conexao()
        sucesso = True
    except LLMError as erro:
        mensagem, sucesso = str(erro), False
    provedor.ultimo_teste_em = timezone.now()
    provedor.ultimo_teste_ok = sucesso
    provedor.ultimo_teste_mensagem = mensagem[:255]
    provedor.save(update_fields=["ultimo_teste_em", "ultimo_teste_ok", "ultimo_teste_mensagem"])
    return sucesso, mensagem
