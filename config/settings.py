"""Configurações do FISCO.IA.

Todos os valores sensíveis ou dependentes de ambiente são lidos de variáveis de
ambiente (arquivo ``.env`` em desenvolvimento). Consulte ``.env.example``.
"""

import tempfile
from pathlib import Path

import environ

BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env(
    DEBUG=(bool, False),
    ALLOWED_HOSTS=(list, ["localhost", "127.0.0.1"]),
    CSRF_TRUSTED_ORIGINS=(list, []),
    FISCO_MODO_DEMO=(bool, False),
    FISCO_LIMIAR_QUALIDADE=(float, 0.6),
    FISCO_PDF_MAX_MB=(int, 30),
    FISCO_SESSAO_MINUTOS=(int, 120),
    FISCO_LLM_TIMEOUT=(int, 180),
)
environ.Env.read_env(BASE_DIR / ".env")

SECRET_KEY = env("SECRET_KEY")
DEBUG = env("DEBUG")
ALLOWED_HOSTS = env("ALLOWED_HOSTS")
CSRF_TRUSTED_ORIGINS = env("CSRF_TRUSTED_ORIGINS")

INSTALLED_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.humanize",
    "apps.core",
    "apps.contas",
    "apps.auditoria",
    "apps.provedores",
    "apps.agentes",
    "apps.analises",
    "apps.empresas",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    # Nada é acessível sem login (exceto views marcadas com @login_not_required).
    "django.contrib.auth.middleware.LoginRequiredMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "apps.core.context_processors.fisco",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

DATABASES = {
    "default": env.db("DATABASE_URL", default="postgres://fisco:fisco@localhost:5432/fisco"),
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LOGIN_URL = "contas:login"
LOGIN_REDIRECT_URL = "core:painel"
LOGOUT_REDIRECT_URL = "contas:login"

LANGUAGE_CODE = "pt-br"
TIME_ZONE = "America/Sao_Paulo"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"
        if not DEBUG
        else "django.contrib.staticfiles.storage.StaticFilesStorage"
    },
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# --- LGPD: sessões fora do banco de dados ------------------------------------
# O resultado das análises fica apenas na sessão do usuário. Para que esse
# conteúdo nunca seja gravado no PostgreSQL, as sessões usam um cache em
# arquivos temporários, com expiração.
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.filebased.FileBasedCache",
        "LOCATION": env(
            "FISCO_SESSION_CACHE_DIR",
            default=str(Path(tempfile.gettempdir()) / "fisco-ia-sessoes"),
        ),
        "TIMEOUT": env("FISCO_SESSAO_MINUTOS") * 60,
    }
}
SESSION_ENGINE = "django.contrib.sessions.backends.cache"
SESSION_COOKIE_AGE = env("FISCO_SESSAO_MINUTOS") * 60
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = True

# Uploads: PDFs nunca vão para MEDIA_ROOT. Arquivos grandes ficam em arquivo
# temporário do Django, removido automaticamente ao fim da requisição.
FISCO_PDF_MAX_MB = env("FISCO_PDF_MAX_MB")
DATA_UPLOAD_MAX_MEMORY_SIZE = 5 * 1024 * 1024
FILE_UPLOAD_MAX_MEMORY_SIZE = 5 * 1024 * 1024

# --- Parâmetros do FISCO.IA ---------------------------------------------------
FISCO_ENCRYPTION_KEY = env("FISCO_ENCRYPTION_KEY")
FISCO_MODO_DEMO = env("FISCO_MODO_DEMO")
FISCO_LIMIAR_QUALIDADE = env("FISCO_LIMIAR_QUALIDADE")
FISCO_LLM_TIMEOUT = env("FISCO_LLM_TIMEOUT")

AVISO_IA = (
    "Conteúdo gerado por inteligência artificial. Deve ser verificado pelo "
    "procurador responsável antes de qualquer utilização processual."
)

if not DEBUG:
    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = "DENY"

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "root": {"handlers": ["console"], "level": "INFO"},
}
