from django.urls import path

from apps.analises import views

app_name = "analises"

urlpatterns = [
    path("nova/", views.NovaAnaliseView.as_view(), name="nova"),
    path("esclarecimentos/", views.PerguntasView.as_view(), name="perguntas"),
    path("resultado/<str:identificador>/", views.ResultadoView.as_view(), name="resultado"),
    path("resultado/<str:identificador>/pdf/", views.ExportarPDFView.as_view(), name="pdf"),
]
