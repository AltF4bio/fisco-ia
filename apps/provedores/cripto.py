"""Criptografia simétrica (Fernet) das chaves de API dos provedores.

A chave mestra vem da variável de ambiente ``FISCO_ENCRYPTION_KEY`` e nunca é
versionada. O banco guarda apenas o texto cifrado.
"""

from __future__ import annotations

from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured


class ChaveIndisponivelError(Exception):
    """A chave armazenada não pôde ser decifrada (ex.: chave mestra trocada)."""


def _fernet() -> Fernet:
    chave_mestra = settings.FISCO_ENCRYPTION_KEY
    if not chave_mestra:
        raise ImproperlyConfigured("Defina FISCO_ENCRYPTION_KEY (consulte .env.example).")
    try:
        return Fernet(chave_mestra.encode() if isinstance(chave_mestra, str) else chave_mestra)
    except ValueError as erro:
        raise ImproperlyConfigured("FISCO_ENCRYPTION_KEY não é uma chave Fernet válida.") from erro


def cifrar(texto: str) -> str:
    return _fernet().encrypt(texto.encode()).decode()


def decifrar(token: str) -> str:
    try:
        return _fernet().decrypt(token.encode()).decode()
    except InvalidToken as erro:
        raise ChaveIndisponivelError(
            "Não foi possível decifrar a chave armazenada. Informe-a novamente."
        ) from erro


def mascarar(chave: str) -> str:
    """Exibe apenas o prefixo e os quatro últimos caracteres (ex.: ``sk-...a1b2``)."""
    chave = chave.strip()
    if len(chave) <= 8:
        return "•" * len(chave)
    prefixo = chave[:3] if chave[:3].endswith("-") else chave[:2]
    return f"{prefixo}...{chave[-4:]}"
