from django.urls import include, path

from apps.core.views import PainelView, saude

urlpatterns = [
    path("", PainelView.as_view(), name="painel"),
    path("saude/", saude, name="saude"),
    path("contas/", include("apps.contas.urls")),
    path("provedores/", include("apps.provedores.urls")),
    path("agentes/", include("apps.agentes.urls")),
]
