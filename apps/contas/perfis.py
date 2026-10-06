"""Perfis de acesso do FISCO.IA (grupos do Django).

- Administrador: gerencia usuários, provedores de IA e agentes.
- Procurador: executa análises e gerencia empresas e suas execuções.

Os perfis são independentes: o administrador não acessa autos nem análises, e o
procurador não acessa telas administrativas nem chaves de API.
"""

from django.contrib.auth.models import AbstractBaseUser, AnonymousUser

ADMINISTRADOR = "Administrador"
PROCURADOR = "Procurador"
PERFIS = (ADMINISTRADOR, PROCURADOR)

Usuario = AbstractBaseUser | AnonymousUser


def _tem_grupo(usuario: Usuario, grupo: str) -> bool:
    if not usuario.is_authenticated or not usuario.is_active:
        return False
    cache = getattr(usuario, "_fisco_grupos", None)
    if cache is None:
        cache = set(usuario.groups.values_list("name", flat=True))
        usuario._fisco_grupos = cache
    return grupo in cache


def eh_administrador(usuario: Usuario) -> bool:
    return _tem_grupo(usuario, ADMINISTRADOR)


def eh_procurador(usuario: Usuario) -> bool:
    return _tem_grupo(usuario, PROCURADOR)


def nome_perfil(usuario: Usuario) -> str:
    perfis = [p for p in PERFIS if _tem_grupo(usuario, p)]
    return " / ".join(perfis) if perfis else "Sem perfil"
