from django.urls import path

from apps.empresas import views

app_name = "empresas"

urlpatterns = [
    path("", views.EmpresaListView.as_view(), name="lista"),
    path("nova/", views.EmpresaCreateView.as_view(), name="nova"),
    path("<int:pk>/", views.EmpresaDetailView.as_view(), name="detalhe"),
    path("<int:pk>/editar/", views.EmpresaUpdateView.as_view(), name="editar"),
    path("<int:pk>/excluir/", views.EmpresaDeleteView.as_view(), name="excluir"),
    path("<int:pk>/execucoes/enviar/", views.EnviarExecucoesView.as_view(), name="enviar"),
    path(
        "<int:pk>/execucoes/exportar.<str:formato>",
        views.ExportarTabelaView.as_view(),
        name="exportar",
    ),
    path("execucoes/<int:pk>/revisar/", views.ExecucaoRevisaoView.as_view(), name="revisar"),
]
