"""Fixtures compartilhadas pela suíte de testes."""

import pytest
from django.contrib.auth.models import Group, User

from apps.contas.perfis import ADMINISTRADOR, PROCURADOR

SENHA = "Senha-de-teste-123"


def _criar_usuario(username: str, perfil: str | None) -> User:
    usuario = User.objects.create_user(
        username=username, password=SENHA, first_name=username.title()
    )
    if perfil:
        usuario.groups.add(Group.objects.get(name=perfil))
    return usuario


@pytest.fixture
def admin_user(db) -> User:
    return _criar_usuario("admin.teste", ADMINISTRADOR)


@pytest.fixture
def procurador(db) -> User:
    return _criar_usuario("procurador.teste", PROCURADOR)


@pytest.fixture
def cliente_admin(client, admin_user):
    client.force_login(admin_user)
    return client


@pytest.fixture
def cliente_procurador(client, procurador):
    client.force_login(procurador)
    return client
