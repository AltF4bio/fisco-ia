import pytest

from apps.analises.services import escopo
from apps.provedores import services as ia
from apps.provedores.llm import LLMResult
from conftest import CABECALHO, MOVIMENTACOES, TEXTO_NAO_FISCAL

TEXTO_FISCAL = "\n".join(CABECALHO + MOVIMENTACOES)


@pytest.fixture
def modelo(agentes):
    return agentes["resumo-cronologico"].modelo


def _espiar(monkeypatch, resposta: str | None = None):
    chamadas = []
    original = ia.gerar

    def falso(modelo, system_prompt, user_content, **opts):
        chamadas.append(opts.get("tarefa"))
        if resposta is not None:
            return LLMResult(texto=resposta, provedor="teste", modelo="x")
        return original(modelo, system_prompt, user_content, **opts)

    monkeypatch.setattr(ia, "gerar", falso)
    return chamadas


def test_execucao_fiscal_e_aceita(modelo, monkeypatch):
    chamadas = _espiar(monkeypatch)
    resultado = escopo.verificar(TEXTO_FISCAL, modelo)
    assert resultado.aceito
    assert {"execução fiscal", "Lei 6.830/80", "CDA", "Fazenda Pública"} <= set(resultado.termos)
    assert chamadas == ["escopo"]  # heurística + checagem rápida pelo modelo


def test_documento_sem_termos_e_recusado_sem_consultar_o_modelo(modelo, monkeypatch):
    chamadas = _espiar(monkeypatch)
    resultado = escopo.verificar("\n".join(TEXTO_NAO_FISCAL), modelo)
    assert not resultado.aceito
    assert chamadas == []


def test_modelo_pode_recusar_mesmo_com_termos(modelo, monkeypatch):
    _espiar(monkeypatch, '{"execucao_fiscal": false, "justificativa": "É uma ação de cobrança."}')
    resultado = escopo.verificar("Ação de cobrança que menciona a Fazenda Pública.", modelo)
    assert not resultado.aceito
    assert resultado.justificativa == "É uma ação de cobrança."


def test_resposta_ilegivel_do_modelo_usa_a_heuristica(modelo, monkeypatch):
    _espiar(monkeypatch, "não sei responder")
    assert escopo.verificar(TEXTO_FISCAL, modelo).aceito
    assert not escopo.verificar("Menciona apenas a Fazenda Pública.", modelo).aceito
