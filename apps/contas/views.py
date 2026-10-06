from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth import views as auth_views
from django.contrib.auth.decorators import login_not_required
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.views.generic import CreateView, FormView, ListView, UpdateView

from apps.auditoria.services import Acao, registrar
from apps.contas.forms import LoginForm, UsuarioCriarForm, UsuarioEditarForm, UsuarioSenhaForm
from apps.core.permissoes import AdministradorMixin

Usuario = get_user_model()


@method_decorator(login_not_required, name="dispatch")
class LoginView(auth_views.LoginView):
    template_name = "contas/login.html"
    authentication_form = LoginForm
    redirect_authenticated_user = True


class LogoutView(auth_views.LogoutView):
    pass


class UsuarioListView(AdministradorMixin, ListView):
    template_name = "contas/usuario_lista.html"
    context_object_name = "usuarios"

    def get_queryset(self):
        return Usuario.objects.prefetch_related("groups").order_by("username")


class UsuarioCreateView(AdministradorMixin, CreateView):
    form_class = UsuarioCriarForm
    template_name = "contas/usuario_form.html"
    success_url = reverse_lazy("contas:usuarios")

    def form_valid(self, form):
        resposta = super().form_valid(form)
        registrar(
            Acao.CADASTRO_USUARIO,
            request=self.request,
            objeto=f"Usuário criado: {self.object.username}",
        )
        messages.success(self.request, "Usuário cadastrado.")
        return resposta


class UsuarioUpdateView(AdministradorMixin, UpdateView):
    model = Usuario
    form_class = UsuarioEditarForm
    template_name = "contas/usuario_form.html"
    success_url = reverse_lazy("contas:usuarios")
    context_object_name = "usuario_editado"

    def get_form_kwargs(self):
        return {**super().get_form_kwargs(), "editor": self.request.user}

    def form_valid(self, form):
        resposta = super().form_valid(form)
        registrar(
            Acao.CADASTRO_USUARIO,
            request=self.request,
            objeto=f"Usuário alterado: {self.object.username}",
        )
        messages.success(self.request, "Usuário atualizado.")
        return resposta


class UsuarioSenhaView(AdministradorMixin, FormView):
    form_class = UsuarioSenhaForm
    template_name = "contas/usuario_senha.html"

    def dispatch(self, request, *args, **kwargs):
        self.usuario_alvo = get_object_or_404(Usuario, pk=kwargs["pk"])
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        return {**super().get_form_kwargs(), "user": self.usuario_alvo}

    def get_context_data(self, **kwargs):
        return {**super().get_context_data(**kwargs), "usuario_editado": self.usuario_alvo}

    def form_valid(self, form):
        form.save()
        registrar(
            Acao.CADASTRO_USUARIO,
            request=self.request,
            objeto=f"Senha redefinida: {self.usuario_alvo.username}",
        )
        messages.success(self.request, "Senha redefinida.")
        return redirect("contas:usuarios")
