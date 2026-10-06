from datetime import timedelta

import pytest
from django.urls import reverse
from django.utils import timezone

from apps.auditoria.models import Acao, LogAuditoria, Resultado
from apps.auditoria.services import registrar


@pytest.fixture
def registros(procurador, admin_user):
    registrar(Acao.ANALISE, usuario=procurador, numero_processo="0000001-00.2020.8.16.0001")
    registrar(Acao.RECUSA_ESCOPO, usuario=procurador, resultado=Resultado.RECUSADO)
    registrar(Acao.CADASTRO_AGENTE, usuario=admin_user, agente="Resumo cronológico")


def test_procurador_nao_acessa_auditoria(cliente_procurador):
    assert cliente_procurador.get(reverse("auditoria:lista")).status_code == 403


def test_admin_consulta_com_filtros(cliente_admin, registros):
    url = reverse("auditoria:lista")
    assert cliente_admin.get(url).context["paginator"].count == 4  # inclui o login do admin

    por_acao = cliente_admin.get(url, {"acao": Acao.RECUSA_ESCOPO}).context["registros"]
    assert [r.acao for r in por_acao] == [Acao.RECUSA_ESCOPO]

    por_usuario = cliente_admin.get(url, {"usuario": "procurador"}).context["paginator"].count
    assert por_usuario == 2

    por_processo = cliente_admin.get(url, {"numero_processo": "0000001"}).context["registros"]
    assert len(por_processo) == 1

    por_resultado = cliente_admin.get(url, {"resultado": "recusado"}).context["registros"]
    assert len(por_resultado) == 1

    amanha = (timezone.localdate() + timedelta(days=1)).isoformat()
    assert cliente_admin.get(url, {"inicio": amanha}).context["paginator"].count == 0


def test_interface_nao_oferece_edicao_nem_exclusao(cliente_admin, registros):
    html = cliente_admin.get(reverse("auditoria:lista")).content.decode()
    assert "Somente leitura" in html
    assert "excluir" not in html.lower()
    resposta = cliente_admin.post(reverse("auditoria:lista"))
    assert resposta.status_code == 405
    assert LogAuditoria.objects.count() == 4
