import pytest
from cryptography.fernet import Fernet
from django.core.exceptions import ImproperlyConfigured
from django.db import connection

from apps.provedores import cripto
from apps.provedores.models import ProvedorIA, TipoProvedor

CHAVE_REAL = "sk-proj-chave-super-secreta-1234a1b2"


def test_cifrar_e_decifrar():
    token = cripto.cifrar(CHAVE_REAL)
    assert token != CHAVE_REAL
    assert CHAVE_REAL not in token
    assert cripto.decifrar(token) == CHAVE_REAL


def test_mascarar_exibe_apenas_prefixo_e_final():
    assert cripto.mascarar(CHAVE_REAL) == "sk-...a1b2"
    assert cripto.mascarar("AIzaSyExemploDeChave9z8y") == "AI...9z8y"
    assert cripto.mascarar("curta") == "•••••"


def test_chave_mestra_diferente_nao_decifra(settings):
    token = cripto.cifrar(CHAVE_REAL)
    settings.FISCO_ENCRYPTION_KEY = Fernet.generate_key().decode()
    with pytest.raises(cripto.ChaveIndisponivelError):
        cripto.decifrar(token)


def test_chave_mestra_ausente(settings):
    settings.FISCO_ENCRYPTION_KEY = ""
    with pytest.raises(ImproperlyConfigured):
        cripto.cifrar("x")


@pytest.mark.django_db
def test_banco_guarda_somente_texto_cifrado():
    provedor = ProvedorIA.objects.get(tipo=TipoProvedor.OPENAI)
    provedor.definir_chave(CHAVE_REAL)
    provedor.save()
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT chave_cifrada, chave_mascarada FROM provedores_provedoria WHERE id = %s",
            [provedor.pk],
        )
        cifrada, mascarada = cursor.fetchone()
    assert CHAVE_REAL not in cifrada
    assert mascarada == "sk-...a1b2"
    provedor.refresh_from_db()
    assert provedor.obter_chave() == CHAVE_REAL
