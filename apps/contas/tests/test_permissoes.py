import pytest
from django.urls import reverse

from apps.contas.perfis import eh_administrador, eh_procurador

URLS_ADMIN = ["contas:usuarios", "contas:usuario_novo"]


@pytest.mark.django_db
def test_paginas_exigem_login(client):
    for nome in ["painel", *URLS_ADMIN]:
        resposta = client.get(reverse(nome))
        assert resposta.status_code == 302
        assert reverse("contas:login") in resposta.url


@pytest.mark.parametrize("nome", URLS_ADMIN)
def test_procurador_nao_acessa_telas_administrativas(cliente_procurador, nome):
    assert cliente_procurador.get(reverse(nome)).status_code == 403


@pytest.mark.parametrize("nome", URLS_ADMIN)
def test_administrador_acessa_telas_administrativas(cliente_admin, nome):
    assert cliente_admin.get(reverse(nome)).status_code == 200


def test_menu_do_procurador_nao_exibe_itens_administrativos(cliente_procurador):
    html = cliente_procurador.get(reverse("painel")).content.decode()
    assert reverse("contas:usuarios") not in html


def test_menu_do_administrador_exibe_usuarios(cliente_admin):
    html = cliente_admin.get(reverse("painel")).content.decode()
    assert reverse("contas:usuarios") in html


def test_funcoes_de_perfil(admin_user, procurador):
    assert eh_administrador(admin_user) and not eh_procurador(admin_user)
    assert eh_procurador(procurador) and not eh_administrador(procurador)


def test_usuario_inativo_nao_tem_perfil(procurador):
    procurador.is_active = False
    assert not eh_procurador(procurador)
