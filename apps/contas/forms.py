from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm, SetPasswordForm, UserCreationForm
from django.contrib.auth.models import Group

from apps.contas.perfis import ADMINISTRADOR, PERFIS, PROCURADOR

Usuario = get_user_model()

PERFIL_CHOICES = [(p, p) for p in PERFIS]


class LoginForm(AuthenticationForm):
    error_messages = {
        "invalid_login": "Usuário ou senha incorretos.",
        "inactive": "Este usuário está inativo.",
    }


class _PerfilMixin(forms.Form):
    perfil = forms.ChoiceField(
        choices=PERFIL_CHOICES,
        help_text=(
            f"{ADMINISTRADOR}: usuários, provedores e agentes. "
            f"{PROCURADOR}: análises, empresas e execuções."
        ),
    )

    def salvar_perfil(self, usuario) -> None:
        usuario.groups.set([Group.objects.get(name=self.cleaned_data["perfil"])])


class UsuarioCriarForm(_PerfilMixin, UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = Usuario
        fields = ("username", "first_name", "last_name", "email")
        labels = {"username": "Usuário", "first_name": "Nome", "last_name": "Sobrenome"}

    def save(self, commit: bool = True):
        usuario = super().save(commit=commit)
        if commit:
            self.salvar_perfil(usuario)
        return usuario


class UsuarioEditarForm(_PerfilMixin, forms.ModelForm):
    class Meta:
        model = Usuario
        fields = ("first_name", "last_name", "email", "is_active")
        labels = {"first_name": "Nome", "last_name": "Sobrenome", "is_active": "Ativo"}

    def __init__(self, *args, editor=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.editor = editor
        grupo = self.instance.groups.filter(name__in=PERFIS).first()
        if grupo:
            self.fields["perfil"].initial = grupo.name

    def clean(self):
        dados = super().clean()
        if self.editor is not None and self.editor.pk == self.instance.pk:
            if not dados.get("is_active"):
                raise forms.ValidationError("Você não pode desativar o próprio usuário.")
            if dados.get("perfil") != ADMINISTRADOR:
                raise forms.ValidationError(
                    "Você não pode remover o próprio perfil de administrador."
                )
        return dados

    def save(self, commit: bool = True):
        usuario = super().save(commit=commit)
        if commit:
            self.salvar_perfil(usuario)
        return usuario


class UsuarioSenhaForm(SetPasswordForm):
    pass
