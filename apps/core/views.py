from django.contrib.auth.decorators import login_not_required
from django.db import connection
from django.http import HttpRequest, JsonResponse
from django.views.generic import TemplateView

from apps.auditoria.models import LogAuditoria


@login_not_required
def saude(request: HttpRequest) -> JsonResponse:
    """Verificação de saúde usada pelo Docker e pelo CI."""
    with connection.cursor() as cursor:
        cursor.execute("SELECT 1")
    return JsonResponse({"status": "ok"})


class PainelView(TemplateView):
    """Painel inicial: atalhos conforme o perfil e últimas atividades do usuário."""

    template_name = "core/painel.html"

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        contexto["atividades"] = LogAuditoria.objects.filter(usuario=self.request.user)[:10]
        return contexto
