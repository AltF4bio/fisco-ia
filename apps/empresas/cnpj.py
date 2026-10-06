"""Validação e formatação de CNPJ.

Aceita o formato numérico tradicional e o CNPJ alfanumérico (IN RFB nº 2.229/2024,
em vigor desde julho de 2026): as 12 primeiras posições podem conter letras
maiúsculas e algarismos; os dois dígitos verificadores continuam numéricos. No
cálculo, cada caractere vale o seu código ASCII menos 48.
"""

from __future__ import annotations

import re

from django.core.exceptions import ValidationError

_PESOS_1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
_PESOS_2 = [6, *_PESOS_1]
_FORMATO = re.compile(r"^[0-9A-Z]{12}\d{2}$")


def normalizar(valor: str) -> str:
    return re.sub(r"[^0-9A-Za-z]", "", valor or "").upper()


def _digito(base: str, pesos: list[int]) -> str:
    soma = sum((ord(c) - 48) * p for c, p in zip(base, pesos, strict=True))
    resto = soma % 11
    return "0" if resto < 2 else str(11 - resto)


def calcular_dv(base12: str) -> str:
    primeiro = _digito(base12, _PESOS_1)
    return primeiro + _digito(base12 + primeiro, _PESOS_2)


def eh_valido(valor: str) -> bool:
    cnpj = normalizar(valor)
    if not _FORMATO.match(cnpj) or len(set(cnpj)) == 1:
        return False
    return cnpj[12:] == calcular_dv(cnpj[:12])


def validar(valor: str) -> None:
    if not eh_valido(valor):
        raise ValidationError("CNPJ inválido.", code="cnpj_invalido")


def formatar(valor: str) -> str:
    c = normalizar(valor)
    if len(c) != 14:
        return valor
    return f"{c[:2]}.{c[2:5]}.{c[5:8]}/{c[8:12]}-{c[12:]}"
