from django.urls import path

from apps.contas import views

app_name = "contas"

urlpatterns = [
    path("entrar/", views.LoginView.as_view(), name="login"),
    path("sair/", views.LogoutView.as_view(), name="logout"),
    path("usuarios/", views.UsuarioListView.as_view(), name="usuarios"),
    path("usuarios/novo/", views.UsuarioCreateView.as_view(), name="usuario_novo"),
    path("usuarios/<int:pk>/", views.UsuarioUpdateView.as_view(), name="usuario_editar"),
    path("usuarios/<int:pk>/senha/", views.UsuarioSenhaView.as_view(), name="usuario_senha"),
]
