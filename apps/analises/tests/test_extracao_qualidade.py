import io

import pytest

from apps.analises.services import extracao
from apps.analises.services.qualidade import avaliar
from conftest import CABECALHO, MOVIMENTACOES, fazer_pdf

TEXTO_BOM = " ".join(CABECALHO + MOVIMENTACOES) * 3


def test_extracao_marca_folhas_e_detecta_numero_do_processo(pdf_execucao):
    extraido = extracao.extrair_texto(io.BytesIO(pdf_execucao), limiar=0.6)
    assert "--- [fl. 1] ---" in extraido.texto
    assert "--- [fl. 2] ---" in extraido.texto
    assert "Mov. 6 - 01/06/2022" in extraido.texto
    assert extraido.numero_processo == "0001234-56.2021.8.16.0004"
    assert extraido.qualidade.paginas == 2


def test_arquivo_invalido_gera_erro():
    with pytest.raises(extracao.PDFInvalidoError):
        extracao.extrair_texto(io.BytesIO(b"isto nao e um pdf"), limiar=0.6)


def test_texto_digitado_tem_qualidade_alta():
    qualidade = avaliar([TEXTO_BOM, TEXTO_BOM], limiar=0.6)
    assert not qualidade.baixa
    assert qualidade.indice > 0.9
    assert qualidade.motivos == []


def test_paginas_sem_texto_indicam_digitalizacao_sem_ocr():
    qualidade = avaliar(["", "", "  ", "Execução fiscal"], limiar=0.6)
    assert qualidade.baixa
    assert qualidade.paginas_sem_texto == 4
    assert any("sem OCR" in motivo for motivo in qualidade.motivos)


def test_caracteres_espurios_indicam_texto_corrompido():
    lixo = "\x00\x01��⌂⌂☐☐" * 300
    qualidade = avaliar([lixo, lixo], limiar=0.6)
    assert qualidade.proporcao_validos < 0.5
    assert any("corrompido" in motivo for motivo in qualidade.motivos)


def test_pdf_sem_paginas():
    assert avaliar([], limiar=0.6).indice == 0


def test_pdf_digitalizado_simulado_tem_alerta():
    pdf = fazer_pdf([["Execução fiscal — CDA"], [], [], []])
    extraido = extracao.extrair_texto(io.BytesIO(pdf), limiar=0.6)
    assert extraido.qualidade.baixa
