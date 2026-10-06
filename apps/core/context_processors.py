from django.conf import settings
from django.http import HttpRequest

from apps.contas.perfis import eh_administrador, eh_procurador, nome_perfil


def fisco(request: HttpRequest) -> dict:
    """Variáveis globais disponíveis em todos os templates (inclusive regras de menu)."""
    usuario = request.user
    return {
        "AVISO_IA": settings.AVISO_IA,
        "MODO_DEMO": settings.FISCO_MODO_DEMO,
        "eh_administrador": eh_administrador(usuario),
        "eh_procurador": eh_procurador(usuario),
        "perfil_usuario": nome_perfil(usuario),
    }
