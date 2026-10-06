from django.contrib.auth.signals import user_logged_in, user_logged_out, user_login_failed
from django.dispatch import receiver

from apps.auditoria.services import Acao, Resultado, registrar


@receiver(user_logged_in)
def _login(sender, request, user, **kwargs):
    registrar(Acao.LOGIN, request=request, usuario=user)


@receiver(user_logged_out)
def _logout(sender, request, user, **kwargs):
    if user is not None:
        registrar(Acao.LOGOUT, request=request, usuario=user)


@receiver(user_login_failed)
def _login_falha(sender, credentials, request=None, **kwargs):
    registrar(
        Acao.LOGIN_FALHA,
        request=request,
        usuario_nome=str(credentials.get("username", ""))[:150],
        resultado=Resultado.ERRO,
    )
