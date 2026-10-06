from django.urls import path

from apps.provedores import views

app_name = "provedores"

urlpatterns = [
    path("", views.ProvedorListView.as_view(), name="lista"),
    path("<int:pk>/", views.ProvedorUpdateView.as_view(), name="editar"),
    path("<int:pk>/testar/", views.TestarConexaoView.as_view(), name="testar"),
    path("<int:provedor_pk>/modelos/novo/", views.ModeloCreateView.as_view(), name="modelo_novo"),
    path("modelos/<int:pk>/", views.ModeloUpdateView.as_view(), name="modelo_editar"),
]
