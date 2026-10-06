from django.urls import path

from apps.agentes import views

app_name = "agentes"

urlpatterns = [
    path("", views.AgenteListView.as_view(), name="lista"),
    path("novo/", views.AgenteCreateView.as_view(), name="novo"),
    path("<int:pk>/", views.AgenteUpdateView.as_view(), name="editar"),
]
