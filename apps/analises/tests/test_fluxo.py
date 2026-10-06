"""Fluxo completo pela interface: upload → escopo → (perguntas) → resultado → PDF."""

import io
from pathlib import Path

import pypdf
import pytest
from django.conf import settings
from django.urls import reverse

from apps.analises.services import sessao
from apps.auditoria.models import Acao, LogAuditoria
from conftest import MOVIMENTACOES, como_upload, fazer_pdf


def _enviar(cliente, pdf: bytes, agente, **extra):
    return cliente.post(
        reverse("analises:nova"),
        {"arquivo": como_upload(pdf), "agente": agente.pk, **extra},
    )


def _arquivos_temporarios() -> list[Path]:
    diretorio = Path(settings.FISCO_TEMP_DIR)
    return list(diretorio.glob("*")) if diretorio.exists() else []


def _textos_do_log() -> str:
    campos = [
        "usuario_nome",
        "numero_processo",
        "agente",
        "provedor",
        "modelo",
        "objeto",
        "detalhe",
    ]
    return " ".join(" ".join(linha) for linha in LogAuditoria.objects.values_list(*campos))


def test_administrador_nao_acessa_analises(cliente_admin):
    assert cliente_admin.get(reverse("analises:nova")).status_code == 403


def test_analise_direta_exibe_resultado_com_aviso(cliente_procurador, agentes, pdf_execucao):
    resposta = _enviar(cliente_procurador, pdf_execucao, agentes["sintese-decisoes"])
    assert resposta.status_code == 302
    html = cliente_procurador.get(resposta.url).content.decode()
    assert "Sentença" in html
    assert settings.AVISO_IA in html
    log = LogAuditoria.objects.get(acao=Acao.ANALISE)
    assert log.numero_processo == "0001234-56.2021.8.16.0004"
    assert log.agente == "Síntese de decisões"
    assert (log.provedor, log.modelo) == ("mock", "mock-fisco")
    assert log.resultado == "sucesso"


def test_html_gerado_pela_ia_e_sanitizado(cliente_procurador, agentes, pdf_execucao, monkeypatch):
    from apps.provedores import services as ia
    from apps.provedores.llm import LLMResult

    original = ia.gerar

    def malicioso(modelo, s, u, **opts):
        if opts.get("tarefa") == "analise":
            return LLMResult("<script>alert(1)</script>[x](javascript:alert(1)) **ok**", "m", "m")
        return original(modelo, s, u, **opts)

    monkeypatch.setattr(ia, "gerar", malicioso)
    resposta = _enviar(cliente_procurador, pdf_execucao, agentes["sintese-decisoes"])
    html = cliente_procurador.get(resposta.url).content.decode()
    assert "<script>alert(1)</script>" not in html
    assert "javascript:" not in html
    assert "<strong>ok</strong>" in html


def test_modo_interativo_pergunta_e_incorpora_respostas(cliente_procurador, agentes, pdf_execucao):
    resposta = _enviar(cliente_procurador, pdf_execucao, agentes["resumo-cronologico"])
    assert resposta.url == reverse("analises:perguntas")
    assert len(_arquivos_temporarios()) == 1  # texto aguardando as respostas

    pagina = cliente_procurador.get(reverse("analises:perguntas"))
    perguntas = pagina.context["form"].perguntas
    assert "Mov. 5" in perguntas[0]["referencia"]

    final = cliente_procurador.post(reverse("analises:perguntas"), {"p1": "Juntado à fl. 30."})
    assert final.status_code == 302
    html = cliente_procurador.get(final.url).content.decode()
    assert "Juntado à fl. 30." in html
    assert _arquivos_temporarios() == []  # LGPD: texto descartado após a análise
    assert sessao.CHAVE_PENDENTE not in cliente_procurador.session
    assert list(
        LogAuditoria.objects.exclude(acao=Acao.LOGIN).values_list("acao", flat=True).order_by("id")
    ) == [
        Acao.ESCLARECIMENTO,
        Acao.ANALISE,
    ]


def test_sem_lacunas_o_modo_interativo_segue_direto(cliente_procurador, agentes):
    pdf = fazer_pdf([[*MOVIMENTACOES[:4], "Execução fiscal da Fazenda Pública — CDA 1/2021"]])
    resposta = _enviar(cliente_procurador, pdf, agentes["resumo-cronologico"])
    assert "/resultado/" in resposta.url


def test_cancelar_descarta_o_texto(cliente_procurador, agentes, pdf_execucao):
    _enviar(cliente_procurador, pdf_execucao, agentes["resumo-cronologico"])
    cliente_procurador.post(reverse("analises:perguntas"), {"cancelar": "1"})
    assert _arquivos_temporarios() == []
    assert cliente_procurador.get(reverse("analises:perguntas")).status_code == 302


def test_documento_fora_do_escopo_e_recusado(cliente_procurador, agentes, pdf_nao_fiscal):
    resposta = _enviar(cliente_procurador, pdf_nao_fiscal, agentes["sintese-decisoes"])
    assert resposta.status_code == 200
    assert "não foi reconhecido como processo de execução fiscal" in resposta.content.decode()
    log = LogAuditoria.objects.exclude(acao=Acao.LOGIN).get()
    assert (log.acao, log.resultado) == (Acao.RECUSA_ESCOPO, "recusado")


def test_alerta_de_baixa_qualidade(cliente_procurador, agentes):
    pdf = fazer_pdf([["Execução fiscal — Fazenda Pública — CDA nº 99/2020"], [], [], []])
    resposta = _enviar(cliente_procurador, pdf, agentes["diagnostico-situacao"])
    html = cliente_procurador.get(resposta.url).content.decode()
    assert "Baixa qualidade de extração" in html
    assert "digitalizado sem OCR, manuscrito ou corrompido" in html


def test_arquivo_que_nao_e_pdf_e_rejeitado(cliente_procurador, agentes):
    resposta = cliente_procurador.post(
        reverse("analises:nova"),
        {
            "arquivo": como_upload(b"texto simples", "autos.pdf"),
            "agente": agentes["sintese-decisoes"].pk,
        },
    )
    assert "Envie um arquivo PDF válido." in resposta.content.decode()


def test_log_nao_guarda_conteudo_dos_autos(cliente_procurador, agentes, pdf_execucao):
    _enviar(cliente_procurador, pdf_execucao, agentes["resumo-cronologico"])
    cliente_procurador.post(reverse("analises:perguntas"), {"p1": "Resposta sigilosa XYZ"})
    _enviar(cliente_procurador, pdf_execucao, agentes["penhora-apropriacao"])
    texto_log = _textos_do_log()
    trechos = [
        "RENAJUD",
        "EMPRESA FICTÍCIA",
        "prescrição",
        "Resposta sigilosa XYZ",
        "150.000",
        "Sentença",
    ]
    for trecho in trechos:
        assert trecho.lower() not in texto_log.lower()


def test_nada_e_gravado_em_media_root(cliente_procurador, agentes, pdf_execucao):
    _enviar(cliente_procurador, pdf_execucao, agentes["sintese-decisoes"])
    media = Path(settings.MEDIA_ROOT)
    assert not media.exists() or not any(media.rglob("*"))


def test_exportacao_em_pdf(cliente_procurador, agentes, pdf_execucao, procurador):
    agente = agentes["penhora-apropriacao"]
    agente.modo_interativo = False
    agente.save()
    resposta = _enviar(cliente_procurador, pdf_execucao, agente)
    identificador = resposta.url.rstrip("/").split("/")[-1]
    arquivo = cliente_procurador.get(reverse("analises:pdf", args=[identificador]))
    assert arquivo["Content-Type"] == "application/pdf"
    assert arquivo.content.startswith(b"%PDF")

    texto = "\n".join(p.extract_text() for p in pypdf.PdfReader(io.BytesIO(arquivo.content)).pages)
    normalizado = " ".join(texto.split())
    assert "FISCO.IA — protótipo acadêmico" in normalizado
    assert "0001234-56.2021.8.16.0004" in normalizado
    assert "Penhora e apropriação de bens" in normalizado
    assert "mock-fisco" in normalizado
    assert procurador.get_full_name() in normalizado
    assert "2022/445566" in normalizado  # protocolo SEFA no corpo
    assert " ".join(settings.AVISO_IA.split()) in normalizado

    log = LogAuditoria.objects.get(acao=Acao.EXPORTACAO)
    assert log.numero_processo == "0001234-56.2021.8.16.0004"


@pytest.mark.django_db
def test_resultado_de_outra_sessao_nao_e_acessivel(client, procurador):
    client.force_login(procurador)
    assert client.get(reverse("analises:resultado", args=["inexistente"])).status_code == 404
