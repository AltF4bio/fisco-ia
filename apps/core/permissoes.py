"""Controle de acesso por perfil, aplicado nas views (os menus usam as mesmas regras)."""

from collections.abc import Callable

from django.contrib.auth.mixins import UserPassesTestMixin

from apps.contas.perfis import eh_administrador, eh_procurador


class _PerfilMixin(UserPassesTestMixin):
    """Usuário autenticado sem o perfil exigido recebe 403 (não é redirecionado)."""

    regra: Callable = staticmethod(lambda usuario: False)
    raise_exception = True

    def test_func(self) -> bool:
        return type(self).regra(self.request.user)


class AdministradorMixin(_PerfilMixin):
    regra = staticmethod(eh_administrador)


class ProcuradorMixin(_PerfilMixin):
    regra = staticmethod(eh_procurador)
