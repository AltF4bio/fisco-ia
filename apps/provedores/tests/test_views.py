import pytest
from django.urls import reverse

from apps.auditoria.models import Acao, LogAuditoria
from apps.provedores.models import ProvedorIA, TipoProvedor

CHAVE = "sk-ant-chave-de-teste-9876zzzz"


@pytest.fixture
def anthropic_provedor(db):
    return ProvedorIA.objects.get(tipo=TipoProvedor.ANTHROPIC)


def test_procurador_nao_acessa_provedores(cliente_procurador, anthropic_provedor):
    assert cliente_procurador.get(reverse("provedores:lista")).status_code == 403
    assert (
        cliente_procurador.get(
            reverse("provedores:editar", args=[anthropic_provedor.pk])
        ).status_code
        == 403
    )
    assert (
        cliente_procurador.post(
            reverse("provedores:testar", args=[anthropic_provedor.pk])
        ).status_code
        == 403
    )


def test_admin_define_chave_e_ela_aparece_somente_mascarada(cliente_admin, anthropic_provedor):
    resposta = cliente_admin.post(
        reverse("provedores:editar", args=[anthropic_provedor.pk]),
        {"ativo": "on", "nova_chave": CHAVE},
    )
    assert resposta.status_code == 302
    anthropic_provedor.refresh_from_db()
    assert anthropic_provedor.disponivel
    assert anthropic_provedor.obter_chave() == CHAVE

    for url in (
        reverse("provedores:lista"),
        reverse("provedores:editar", args=[anthropic_provedor.pk]),
    ):
        html = cliente_admin.get(url).content.decode()
        assert CHAVE not in html
        assert "sk-...zzzz" in html

    log = LogAuditoria.objects.get(acao=Acao.CADASTRO_PROVEDOR)
    assert CHAVE not in str(log.__dict__)


def test_nao_ativa_provedor_sem_chave(cliente_admin, anthropic_provedor):
    resposta = cliente_admin.post(
        reverse("provedores:editar", args=[anthropic_provedor.pk]), {"ativo": "on"}
    )
    assert resposta.status_code == 200
    anthropic_provedor.refresh_from_db()
    assert not anthropic_provedor.ativo


def test_lista_exibe_lembrete_de_confidencialidade(cliente_admin):
    html = cliente_admin.get(reverse("provedores:lista")).content.decode()
    assert "vedem o uso dos dados para treinamento" in html


def test_testar_conexao_registra_resultado_e_auditoria(cliente_admin):
    mock = ProvedorIA.objects.get(tipo=TipoProvedor.MOCK)
    resposta = cliente_admin.post(reverse("provedores:testar", args=[mock.pk]))
    assert resposta.status_code == 200
    assert "Provedor de demonstração ativo" in resposta.content.decode()
    mock.refresh_from_db()
    assert mock.ultimo_teste_ok is True
    assert LogAuditoria.objects.filter(acao=Acao.TESTE_PROVEDOR, provedor="mock").exists()


def test_testar_conexao_sem_chave_falha(cliente_admin, anthropic_provedor):
    resposta = cliente_admin.post(reverse("provedores:testar", args=[anthropic_provedor.pk]))
    assert "não tem chave de API" in resposta.content.decode()
    anthropic_provedor.refresh_from_db()
    assert anthropic_provedor.ultimo_teste_ok is False


def test_admin_cadastra_modelo(cliente_admin, anthropic_provedor):
    resposta = cliente_admin.post(
        reverse("provedores:modelo_novo", args=[anthropic_provedor.pk]),
        {
            "identificador": "claude-novo",
            "nome_exibicao": "Claude Novo",
            "limite_contexto_tokens": 100000,
            "max_saida_tokens": 8000,
            "ativo": "on",
        },
    )
    assert resposta.status_code == 302
    assert anthropic_provedor.modelos.filter(identificador="claude-novo").exists()
