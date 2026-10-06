import pytest

from apps.analises.services import blocos, executor, interativo
from apps.provedores import services as ia
from apps.provedores.llm import LLMResult
from conftest import CABECALHO, MOVIMENTACOES


def _autos(folhas: int) -> str:
    conteudo = "\n".join(CABECALHO + MOVIMENTACOES)
    return "\n\n".join(f"--- [fl. {i}] ---\n{conteudo}" for i in range(1, folhas + 1))


@pytest.fixture
def espiao(monkeypatch):
    chamadas = []
    original = ia.gerar

    def falso(modelo, system_prompt, user_content, **opts):
        chamadas.append(opts.get("tarefa"))
        return original(modelo, system_prompt, user_content, **opts)

    monkeypatch.setattr(ia, "gerar", falso)
    return chamadas


# --- divisão em blocos ---------------------------------------------------------


def test_dividir_respeita_o_orcamento_e_preserva_as_folhas():
    texto = _autos(20)
    partes = blocos.dividir(texto, orcamento_tokens=800)
    assert len(partes) > 1
    assert "".join(partes) == texto
    assert all(blocos.estimar_tokens(p) <= 800 for p in partes)
    assert all(p.startswith("--- [fl.") for p in partes)


def test_folha_maior_que_o_orcamento_e_fatiada():
    texto = "--- [fl. 1] ---\n" + "x" * 10_000
    partes = blocos.dividir(texto, orcamento_tokens=500)
    assert len(partes) > 1
    assert "".join(partes) == texto


# --- execução (map-reduce) -------------------------------------------------------


def test_texto_pequeno_usa_uma_unica_chamada(agentes, espiao):
    resultado = executor.analisar(agentes["resumo-cronologico"], _autos(1))
    assert espiao == ["analise"]
    assert resultado.blocos == 1
    assert "| 6 | 01/06/2022 |" in resultado.texto


def test_texto_extenso_usa_map_reduce(agentes, espiao):
    agente = agentes["resumo-cronologico"]  # modelo de demonstração: contexto pequeno
    texto = _autos(40)
    assert not blocos.cabe_no_contexto(
        texto, blocos.orcamento_entrada(agente.modelo, agente.prompt)
    )
    resultado = executor.analisar(agente, texto)
    assert resultado.blocos > 1
    assert espiao.count("parcial") == resultado.blocos
    assert espiao[-1] == "consolidacao"
    assert "Consolidação de análises parciais" in resultado.texto
    assert resultado.texto.count("| 6 | 01/06/2022 |") == 1  # repetições eliminadas


def test_troca_de_provedor_reflete_no_resultado(agentes, monkeypatch):
    monkeypatch.setattr(
        ia,
        "gerar",
        lambda modelo, s, u, **o: LLMResult(texto="ok", provedor="anthropic", modelo="claude-x"),
    )
    resultado = executor.analisar(agentes["diagnostico-situacao"], _autos(1))
    assert (resultado.provedor, resultado.modelo) == ("anthropic", "claude-x")


# --- modo interativo -------------------------------------------------------------


def test_lacunas_geram_perguntas_estruturadas(agentes):
    perguntas = interativo.gerar_perguntas(agentes["resumo-cronologico"], _autos(1))
    assert len(perguntas) == 1
    assert perguntas[0].id == "p1"
    assert perguntas[0].referencia == "Mov. 5"


def test_sem_lacunas_nao_ha_perguntas(agentes):
    texto = _autos(1).replace("Documento não juntado aos autos.", "")
    assert interativo.gerar_perguntas(agentes["resumo-cronologico"], texto) == []


def test_resposta_malformada_ou_excessiva_e_validada(agentes, monkeypatch):
    itens = ",".join(f'{{"pergunta": "P{i}?", "referencia": "Mov. {i}"}}' for i in range(9))
    monkeypatch.setattr(
        ia,
        "gerar",
        lambda *a, **o: LLMResult(
            texto=f'```json\n{{"perguntas": [{itens}, {{"x": 1}}, "lixo"]}}\n```',
            provedor="t",
            modelo="t",
        ),
    )
    perguntas = interativo.gerar_perguntas(agentes["resumo-cronologico"], _autos(1))
    assert [p.id for p in perguntas] == ["p1", "p2", "p3", "p4", "p5"]

    monkeypatch.setattr(ia, "gerar", lambda *a, **o: LLMResult("sem json", "t", "t"))
    assert interativo.gerar_perguntas(agentes["resumo-cronologico"], _autos(1)) == []


def test_respostas_sao_incorporadas_a_analise(agentes):
    perguntas = [interativo.Pergunta("p1", "O documento foi juntado?", "Mov. 5")]
    esclarecimentos = interativo.formatar_esclarecimentos(perguntas, {"p1": "Sim, à fl. 30."})
    resultado = executor.analisar(agentes["resumo-cronologico"], _autos(1), esclarecimentos)
    assert "Esclarecimentos do procurador considerados" in resultado.texto
    assert "Sim, à fl. 30." in resultado.texto
