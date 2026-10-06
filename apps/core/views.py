from django.contrib.auth.decorators import login_not_required
from django.db import connection
from django.http import HttpRequest, JsonResponse


@login_not_required
def saude(request: HttpRequest) -> JsonResponse:
    """Verificação de saúde usada pelo Docker e pelo CI."""
    with connection.cursor() as cursor:
        cursor.execute("SELECT 1")
    return JsonResponse({"status": "ok"})
