import pytest
from django.contrib.auth.models import User
from django.urls import reverse

from apps.auditoria.models import Acao, LogAuditoria
from apps.contas.perfis import PROCURADOR, eh_procurador
from conftest import SENHA


def test_login_e_logout_sao_auditados(client, procurador):
    resposta = client.post(
        reverse("contas:login"), {"username": procurador.username, "password": SENHA}
    )
    assert resposta.status_code == 302
    client.post(reverse("contas:logout"))
    acoes = list(LogAuditoria.objects.values_list("acao", flat=True))
    assert Acao.LOGIN in acoes and Acao.LOGOUT in acoes


def test_login_invalido_e_auditado_sem_senha(client, procurador):
    client.post(
        reverse("contas:login"), {"username": procurador.username, "password": "errada-123"}
    )
    log = LogAuditoria.objects.get(acao=Acao.LOGIN_FALHA)
    assert log.usuario_nome == procurador.username
    assert "errada-123" not in str(log.__dict__)


def test_admin_cria_usuario_com_perfil(cliente_admin):
    resposta = cliente_admin.post(
        reverse("contas:usuario_novo"),
        {
            "username": "nova.procuradora",
            "first_name": "Nova",
            "last_name": "Procuradora",
            "email": "nova@exemplo.com",
            "perfil": PROCURADOR,
            "password1": "Uma-senha-forte-987",
            "password2": "Uma-senha-forte-987",
        },
    )
    assert resposta.status_code == 302
    assert eh_procurador(User.objects.get(username="nova.procuradora"))
    assert LogAuditoria.objects.filter(acao=Acao.CADASTRO_USUARIO).exists()


def test_admin_nao_pode_se_desativar(cliente_admin, admin_user):
    resposta = cliente_admin.post(
        reverse("contas:usuario_editar", args=[admin_user.pk]),
        {"first_name": "A", "last_name": "", "email": "", "perfil": "Administrador"},
    )
    assert resposta.status_code == 200
    admin_user.refresh_from_db()
    assert admin_user.is_active


@pytest.mark.django_db
def test_admin_redefine_senha(cliente_admin, procurador):
    resposta = cliente_admin.post(
        reverse("contas:usuario_senha", args=[procurador.pk]),
        {"new_password1": "Outra-senha-forte-321", "new_password2": "Outra-senha-forte-321"},
    )
    assert resposta.status_code == 302
    procurador.refresh_from_db()
    assert procurador.check_password("Outra-senha-forte-321")
