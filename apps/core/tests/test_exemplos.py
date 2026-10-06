"""Os PDFs fictícios de demonstração percorrem o fluxo real (com o MockProvider)."""

import importlib.util
from decimal import Decimal
from pathlib import Path

import pytest
from django.conf import settings
from django.urls import reverse

from apps.empresas.models import Empresa, ExecucaoFiscal, Situacao
from conftest import como_upload

SCRIPT = Path(settings.BASE_DIR) / "scripts" / "gerar_pdfs_ficticios.py"


@pytest.fixture(scope="module")
def exemplos(tmp_path_factory) -> dict[str, bytes]:
    especificacao = importlib.util.spec_from_file_location("gerar_pdfs_ficticios", SCRIPT)
    modulo = importlib.util.module_from_spec(especificacao)
    especificacao.loader.exec_module(modulo)
    pasta = tmp_path_factory.mktemp("exemplos")
    for nome, gerar in modulo.GERADORES.items():
        gerar(pasta / nome)
    return {p.stem: p.read_bytes() for p in pasta.glob("*.pdf")}


def _analisar(cliente, pdf: bytes, agente):
    return cliente.post(
        reverse("analises:nova"), {"arquivo": como_upload(pdf), "agente": agente.pk}
    )


def test_exemplo_interativo(cliente_procurador, agentes, exemplos):
    resposta = _analisar(
        cliente_procurador, exemplos["execucao_fiscal_01_modo_interativo"],
        agentes["resumo-cronologico"],
    )  # fmt: skip
    assert resposta.url == reverse("analises:perguntas")
    perguntas = cliente_procurador.get(resposta.url).context["form"].perguntas
    assert len(perguntas) == 2
    final = cliente_procurador.post(resposta.url, {"p1": "Benfeitorias: galpão.", "p2": ""})
    html = cliente_procurador.get(final.url).content.decode()
    assert "Benfeitorias: galpão." in html
    assert "0004567-89.2019.8.16.0014" in html


def test_exemplo_extenso_usa_map_reduce(cliente_procurador, agentes, exemplos):
    resposta = _analisar(
        cliente_procurador, exemplos["execucao_fiscal_02_extensa_map_reduce"],
        agentes["diagnostico-situacao"],
    )  # fmt: skip
    pagina = cliente_procurador.get(resposta.url)
    assert pagina.context["resultado"]["blocos"] > 1
    assert "suspenso" in pagina.content.decode()


def test_exemplo_digitalizado_gera_alerta(cliente_procurador, agentes, exemplos):
    resposta = _analisar(
        cliente_procurador, exemplos["execucao_fiscal_03_digitalizada_sem_ocr"],
        agentes["sintese-decisoes"],
    )  # fmt: skip
    assert "Baixa qualidade de extração" in cliente_procurador.get(resposta.url).content.decode()


def test_exemplo_fora_do_escopo_e_recusado(cliente_procurador, agentes, exemplos):
    resposta = _analisar(
        cliente_procurador, exemplos["documento_fora_do_escopo"], agentes["sintese-decisoes"]
    )
    assert "Documento fora do escopo" in resposta.content.decode()


def test_exemplos_alimentam_a_tabela_consolidada(cliente_procurador, agentes, exemplos):
    empresa = Empresa.objects.create(razao_social="Metalúrgica", cnpj="45723174000110")
    cliente_procurador.post(
        reverse("empresas:enviar", args=[empresa.pk]),
        {
            "arquivos": [
                como_upload(exemplos["execucao_fiscal_01_modo_interativo"], "a.pdf"),
                como_upload(exemplos["execucao_fiscal_02_extensa_map_reduce"], "b.pdf"),
            ]
        },
    )
    primeira = ExecucaoFiscal.objects.get(numero_processo="0004567-89.2019.8.16.0014")
    assert primeira.valor_executado == Decimal("487352.19")
    assert primeira.apropriacoes[0]["protocolo_sefa"] == "2021/0387741"
    assert primeira.acao_imediata
    assert {"Prescrição", "Nulidade da CDA"} <= set(primeira.teses_defesa)
    segunda = ExecucaoFiscal.objects.get(numero_processo="0012890-33.2017.8.16.0004")
    assert segunda.situacao == Situacao.SUSPENSO
    assert not segunda.acao_imediata
