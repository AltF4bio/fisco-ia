"""Registro de operações no log de auditoria."""

from django.contrib.auth.models import AbstractBaseUser, AnonymousUser
from django.http import HttpRequest

from apps.auditoria.models import Acao, LogAuditoria, Resultado

__all__ = ["Acao", "Resultado", "registrar"]

_LIMITE_DETALHE = 255


def _ip_do_request(request: HttpRequest | None) -> str | None:
    if request is None:
        return None
    return request.META.get("REMOTE_ADDR") or None


def registrar(
    acao: Acao | str,
    *,
    request: HttpRequest | None = None,
    usuario: AbstractBaseUser | AnonymousUser | None = None,
    usuario_nome: str = "",
    resultado: Resultado | str = Resultado.SUCESSO,
    numero_processo: str = "",
    agente: str = "",
    provedor: str = "",
    modelo: str = "",
    objeto: str = "",
    detalhe: str = "",
) -> LogAuditoria:
    """Grava um registro de auditoria contendo somente metadados.

    Nunca passe aqui trechos dos autos, do texto extraído ou da análise gerada.
    """
    if usuario is None and request is not None:
        usuario = request.user
    autenticado = usuario is not None and usuario.is_authenticated
    return LogAuditoria.objects.create(
        acao=acao,
        resultado=resultado,
        usuario=usuario if autenticado else None,
        usuario_nome=(usuario.get_username() if autenticado else usuario_nome)[:150],
        numero_processo=numero_processo[:30],
        agente=agente[:120],
        provedor=provedor[:30],
        modelo=modelo[:100],
        objeto=objeto[:200],
        detalhe=detalhe[:_LIMITE_DETALHE],
        ip=_ip_do_request(request),
    )
