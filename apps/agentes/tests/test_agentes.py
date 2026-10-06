import pytest
from django.core.management import call_command
from django.urls import reverse

from apps.agentes.models import Agente
from apps.agentes.prompts import AGENTES
from apps.auditoria.models import Acao, LogAuditoria
from apps.provedores.models import ModeloIA, ProvedorIA, TipoProvedor


@pytest.fixture
def mock_ativo(db):
    ProvedorIA.objects.filter(tipo=TipoProvedor.MOCK).update(ativo=True)
    return ModeloIA.objects.get(identificador="mock-fisco")


@pytest.mark.django_db
def test_seed_agentes_cria_os_cinco_agentes_e_o_interno():
    call_command("seed_agentes")
    assert Agente.objects.selecionaveis().count() == 5
    assert Agente.objects.filter(interno=True, slug="extracao-estruturada").exists()
    for agente in Agente.objects.filter(interno=False):
        assert "exclusivamente no conteúdo dos autos" in agente.prompt
        assert "Não consta dos autos." in agente.prompt
        assert "movimentação" in agente.prompt


@pytest.mark.django_db
def test_seed_agentes_e_idempotente_e_preserva_modelo_escolhido():
    call_command("seed_agentes")
    agente = Agente.objects.get(slug="sintese-decisoes")
    outro = ModeloIA.objects.get(identificador="claude-haiku-4-5")
    agente.modelo = outro
    agente.save()
    call_command("seed_agentes")
    agente.refresh_from_db()
    assert agente.modelo == outro
    assert Agente.objects.count() == len(AGENTES) + 1


@pytest.mark.django_db
def test_seed_agentes_com_modelo_explicito():
    call_command("seed_agentes", modelo="claude-sonnet-5-5")
    assert set(Agente.objects.values_list("modelo__identificador", flat=True)) == {
        "claude-sonnet-5-5"
    }


def test_procurador_nao_acessa_agentes(cliente_procurador):
    assert cliente_procurador.get(reverse("agentes:lista")).status_code == 403
    assert cliente_procurador.get(reverse("agentes:novo")).status_code == 403


def test_formulario_lista_apenas_modelos_de_provedores_ativos(cliente_admin, mock_ativo):
    form = cliente_admin.get(reverse("agentes:novo")).context["form"]
    tipos = {m.provedor.tipo for m in form.fields["modelo"].queryset}
    assert tipos == {"mock"}


def test_admin_cadastra_agente_e_auditoria_registra(cliente_admin, mock_ativo):
    resposta = cliente_admin.post(
        reverse("agentes:novo"),
        {
            "nome": "Agente de teste",
            "slug": "agente-teste",
            "descricao": "Descrição",
            "prompt": "Responda apenas com base nos autos.",
            "modelo": mock_ativo.pk,
            "modo_interativo": "on",
            "ativo": "on",
        },
    )
    assert resposta.status_code == 302
    agente = Agente.objects.get(slug="agente-teste")
    assert agente.modo_interativo
    log = LogAuditoria.objects.get(acao=Acao.CADASTRO_AGENTE)
    assert log.agente == "Agente de teste" and log.modelo == "mock-fisco"


def test_admin_nao_vincula_modelo_de_provedor_inativo(cliente_admin, mock_ativo):
    inativo = ModeloIA.objects.get(identificador="gpt-6.1-sol")
    resposta = cliente_admin.post(
        reverse("agentes:novo"),
        {
            "nome": "X",
            "slug": "x",
            "descricao": "d",
            "prompt": "p",
            "modelo": inativo.pk,
            "ativo": "on",
        },
    )
    assert resposta.status_code == 200
    assert not Agente.objects.filter(slug="x").exists()
