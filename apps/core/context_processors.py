from django.conf import settings
from django.http import HttpRequest


def fisco(request: HttpRequest) -> dict:
    """Variáveis globais disponíveis em todos os templates."""
    return {
        "AVISO_IA": settings.AVISO_IA,
        "MODO_DEMO": settings.FISCO_MODO_DEMO,
    }
