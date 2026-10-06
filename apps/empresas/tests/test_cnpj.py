import pytest
from django.core.exceptions import ValidationError

from apps.empresas import cnpj


@pytest.mark.parametrize("valor", ["11.222.333/0001-81", "11222333000181", "12ABC34501DE35"])
def test_cnpjs_validos(valor):
    assert cnpj.eh_valido(valor)


@pytest.mark.parametrize(
    "valor", ["11.222.333/0001-82", "00000000000000", "123", "", "12ABC34501DE36", "1222333000181A"]
)
def test_cnpjs_invalidos(valor):
    assert not cnpj.eh_valido(valor)
    with pytest.raises(ValidationError):
        cnpj.validar(valor)


def test_formatacao_e_normalizacao():
    assert cnpj.normalizar("12.abc.345/01de-35") == "12ABC34501DE35"
    assert cnpj.formatar("11222333000181") == "11.222.333/0001-81"
