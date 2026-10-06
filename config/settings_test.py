"""Configurações para a suíte de testes (pytest).

Define valores padrão seguros para que os testes rodem sem ``.env`` e sem chaves
reais. Os provedores de IA são sempre substituídos pelo MockProvider.
"""

import os

os.environ.setdefault("SECRET_KEY", "chave-apenas-para-testes")
# Chave Fernet fixa e pública, usada exclusivamente na suíte de testes.
os.environ.setdefault("FISCO_ENCRYPTION_KEY", "q0Tq9cTq1x0n7zj3m8Bf2y8b5P0cHq3o6aHqvJ2n0hU=")
os.environ.setdefault("FISCO_MODO_DEMO", "True")

from config.settings import *  # noqa: F403

CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
STORAGES["staticfiles"]["BACKEND"] = "django.contrib.staticfiles.storage.StaticFilesStorage"  # noqa: F405
FISCO_MODO_DEMO = True
MIDDLEWARE = [m for m in MIDDLEWARE if "whitenoise" not in m]  # noqa: F405
