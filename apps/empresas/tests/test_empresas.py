import pytest
from django.urls import reverse

from apps.auditoria.models import Acao, LogAuditoria
from apps.empresas.models import Empresa


def test_administrador_nao_acessa_empresas(cliente_admin):
    assert cliente_admin.get(reverse("empresas:lista")).status_code == 403
    assert cliente_admin.get(reverse("empresas:nova")).status_code == 403


def test_procurador_cadastra_empresa_com_cnpj_valido(cliente_procurador):
    resposta = cliente_procurador.post(
        reverse("empresas:nova"),
        {
            "razao_social": "Comércio Fictício Ltda.",
            "cnpj": "11.222.333/0001-81",
            "observacoes": "",
        },
    )
    assert resposta.status_code == 302
    empresa = Empresa.objects.get()
    assert empresa.cnpj == "11222333000181"
    assert empresa.cnpj_formatado == "11.222.333/0001-81"
    assert LogAuditoria.objects.filter(acao=Acao.CADASTRO_EMPRESA).exists()


def test_cnpj_invalido_ou_duplicado_e_rejeitado(cliente_procurador):
    Empresa.objects.create(razao_social="A", cnpj="11222333000181")
    for valor in ("11.222.333/0001-82", "11.222.333/0001-81"):
        resposta = cliente_procurador.post(
            reverse("empresas:nova"), {"razao_social": "B", "cnpj": valor}
        )
        assert resposta.status_code == 200
    assert Empresa.objects.count() == 1


@pytest.mark.django_db
def test_edicao_e_exclusao(cliente_procurador):
    empresa = Empresa.objects.create(razao_social="A", cnpj="11222333000181")
    cliente_procurador.post(
        reverse("empresas:editar", args=[empresa.pk]),
        {"razao_social": "A Renomeada", "cnpj": "11222333000181", "observacoes": "obs"},
    )
    empresa.refresh_from_db()
    assert empresa.razao_social == "A Renomeada"
    cliente_procurador.post(reverse("empresas:excluir", args=[empresa.pk]))
    assert not Empresa.objects.exists()
    assert LogAuditoria.objects.filter(acao=Acao.CADASTRO_EMPRESA).count() == 2


def test_lista_mostra_busca(cliente_procurador):
    Empresa.objects.create(razao_social="Alfa Fictícia", cnpj="11222333000181")
    Empresa.objects.create(razao_social="Beta Fictícia", cnpj="12ABC34501DE35")
    contexto = cliente_procurador.get(reverse("empresas:lista"), {"busca": "beta"}).context
    assert [e.razao_social for e in contexto["empresas"]] == ["Beta Fictícia"]
