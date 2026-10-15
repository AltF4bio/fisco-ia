import csv
import io
from decimal import Decimal

import pypdf
import pytest
from django.conf import settings
from django.urls import reverse

from apps.auditoria.models import Acao, LogAuditoria
from apps.empresas.models import Empresa, ExecucaoFiscal, Situacao
from apps.empresas.services import consolidacao
from conftest import CABECALHO, MOVIMENTACOES, como_upload, fazer_pdf

NUMERO = "0001234-56.2021.8.16.0004"


@pytest.fixture
def empresa(db):
    return Empresa.objects.create(razao_social="Empresa Fictícia Ltda.", cnpj="11222333000181")


@pytest.fixture
def outra_empresa(db):
    return Empresa.objects.create(razao_social="Outra Fictícia S.A.", cnpj="12ABC34501DE35")


def _enviar(cliente, empresa, *pdfs):
    return cliente.post(
        reverse("empresas:enviar", args=[empresa.pk]),
        {"arquivos": [como_upload(pdf, f"autos{i}.pdf") for i, pdf in enumerate(pdfs)]},
        follow=True,
    )


# --- validação do JSON -----------------------------------------------------------


def test_validacao_converte_e_descarta_dados_invalidos():
    dados = consolidacao.validar_dados(
        {
            "numero_processo": "invalido",
            "cdas": "CDA 1",
            "valor_executado": "1.234,56",
            "bens_penhorados": [None, "", "Veículo"],
            "apropriacoes": [{"descricao": "R$ 10,00", "protocolo_sefa": "2022/1"}, "texto"],
            "teses_defesa": ["Prescrição", "Prescrição"],
            "situacao": "inventada",
            "acao_imediata": "sim",
        },
        numero_reserva=NUMERO,
    )
    assert dados.numero_processo == NUMERO
    assert dados.cdas == ["CDA 1"]
    assert dados.valor_executado == Decimal("1234.56")
    assert dados.bens_penhorados == ["Veículo"]
    assert dados.apropriacoes[0] == {"descricao": "R$ 10,00", "protocolo_sefa": "2022/1"}
    assert dados.teses_defesa == ["Prescrição"]
    assert dados.situacao == Situacao.EM_ANDAMENTO
    assert dados.acao_imediata is True


def test_sem_numero_do_processo_nao_consolida():
    with pytest.raises(consolidacao.ConsolidacaoError):
        consolidacao.validar_dados({"numero_processo": ""})


# --- upsert ------------------------------------------------------------------------


def test_upsert_cria_e_depois_atualiza_pela_chave(empresa):
    dados = consolidacao.DadosExecucao(numero_processo=NUMERO, valor_executado=Decimal("10"))
    execucao, criada, _ = consolidacao.upsert(empresa, dados)
    assert criada
    novos = consolidacao.DadosExecucao(
        numero_processo=NUMERO, valor_executado=Decimal("20"), situacao=Situacao.SUSPENSO
    )
    execucao, criada, _ = consolidacao.upsert(empresa, novos)
    assert not criada
    assert ExecucaoFiscal.objects.count() == 1
    assert execucao.valor_executado == Decimal("20")
    assert execucao.situacao == Situacao.SUSPENSO


def test_upsert_preserva_campos_revisados(empresa):
    execucao, _, _ = consolidacao.upsert(
        empresa, consolidacao.DadosExecucao(numero_processo=NUMERO, valor_executado=Decimal("10"))
    )
    execucao.valor_executado = Decimal("99")
    execucao.campos_revisados = ["valor_executado"]
    execucao.revisado_manualmente = True
    execucao.save()

    novos = consolidacao.DadosExecucao(
        numero_processo=NUMERO, valor_executado=Decimal("20"), teses_defesa=["Prescrição"]
    )
    execucao, _, preservados = consolidacao.upsert(empresa, novos)
    assert preservados == ["valor_executado"]
    assert execucao.valor_executado == Decimal("99")  # a revisão humana prevalece
    assert execucao.teses_defesa == ["Prescrição"]  # campo não revisado é atualizado


def test_processo_de_outra_empresa_nao_e_sobrescrito(empresa, outra_empresa):
    consolidacao.upsert(empresa, consolidacao.DadosExecucao(numero_processo=NUMERO))
    with pytest.raises(consolidacao.ConsolidacaoError):
        consolidacao.upsert(outra_empresa, consolidacao.DadosExecucao(numero_processo=NUMERO))


# --- fluxo pela interface ------------------------------------------------------------


def test_envio_de_pdf_alimenta_a_tabela(cliente_procurador, agentes, empresa, pdf_execucao):
    resposta = _enviar(cliente_procurador, empresa, pdf_execucao)
    assert "incluído na tabela" in resposta.content.decode()
    execucao = ExecucaoFiscal.objects.get()
    assert execucao.numero_processo == NUMERO
    assert execucao.cdas == ["20210001234-5"]
    assert execucao.valor_executado == Decimal("150000.00")
    assert execucao.apropriacoes[0]["protocolo_sefa"] == "2022/445566"
    assert "Prescrição" in execucao.teses_defesa
    assert execucao.situacao == Situacao.AGUARDANDO_MANIFESTACAO
    assert execucao.acao_imediata
    log = LogAuditoria.objects.get(acao=Acao.EXTRACAO_EXECUCAO)
    assert log.numero_processo == NUMERO and log.resultado == "sucesso"


def test_reenvio_atualiza_a_mesma_linha(cliente_procurador, agentes, empresa, pdf_execucao):
    _enviar(cliente_procurador, empresa, pdf_execucao)
    resposta = _enviar(cliente_procurador, empresa, pdf_execucao)
    assert "atualizado na tabela" in resposta.content.decode()
    assert ExecucaoFiscal.objects.count() == 1


def test_envio_de_varios_pdfs_e_recusa_fora_do_escopo(
    cliente_procurador, agentes, empresa, pdf_execucao, pdf_nao_fiscal
):
    linhas = [linha.replace(NUMERO, "0009999-11.2020.8.16.0001") for linha in CABECALHO]
    outro = fazer_pdf([[*linhas, *MOVIMENTACOES[:2]]])
    resposta = _enviar(cliente_procurador, empresa, pdf_execucao, outro, pdf_nao_fiscal)
    html = resposta.content.decode()
    assert ExecucaoFiscal.objects.count() == 2
    assert "não foi reconhecido como processo de execução fiscal" in html
    assert LogAuditoria.objects.filter(acao=Acao.RECUSA_ESCOPO).count() == 1


def test_revisao_manual_marca_campos_e_audita(cliente_procurador, agentes, empresa, pdf_execucao):
    _enviar(cliente_procurador, empresa, pdf_execucao)
    execucao = ExecucaoFiscal.objects.get()
    resposta = cliente_procurador.post(
        reverse("empresas:revisar", args=[execucao.pk]),
        {
            "numero_processo": execucao.numero_processo,
            "cdas": "20210001234-5\n20210009999-0",
            "valor_executado": "150000.00",
            "bens_penhorados": "\n".join(execucao.bens_penhorados),
            "apropriacoes": "Valor apropriado | 2022/445566",
            "teses_defesa": "\n".join(execucao.teses_defesa),
            "situacao": execucao.situacao,
            "situacao_detalhe": execucao.situacao_detalhe,
            "acao_imediata": "on",
        },
    )
    assert resposta.status_code == 302
    execucao.refresh_from_db()
    assert execucao.revisado_manualmente
    assert execucao.campos_revisados == ["apropriacoes", "cdas"]
    assert execucao.cdas == ["20210001234-5", "20210009999-0"]
    log = LogAuditoria.objects.get(acao=Acao.REVISAO_EXECUCAO)
    assert "cdas" in log.objeto

    # Nova extração do mesmo processo não desfaz a revisão humana.
    _enviar(cliente_procurador, empresa, pdf_execucao)
    execucao.refresh_from_db()
    assert execucao.cdas == ["20210001234-5", "20210009999-0"]


def test_tabela_filtra_ordena_soma_e_destaca(cliente_procurador, empresa):
    ExecucaoFiscal.objects.create(
        empresa=empresa, numero_processo="0000001-00.2020.8.16.0001",
        valor_executado=Decimal("100.00"), situacao=Situacao.SUSPENSO,
    )  # fmt: skip
    ExecucaoFiscal.objects.create(
        empresa=empresa, numero_processo="0000002-00.2020.8.16.0001",
        valor_executado=Decimal("250.50"), situacao=Situacao.CUMPRIMENTO, acao_imediata=True,
    )  # fmt: skip
    url = reverse("empresas:detalhe", args=[empresa.pk])

    contexto = cliente_procurador.get(url).context
    assert contexto["totais"] == {"quantidade": 2, "valor": Decimal("350.50"), "acao_imediata": 1}
    html = cliente_procurador.get(url).content.decode()
    assert "linha-acao-imediata" in html
    assert settings.AVISO_IA in html

    filtrado = cliente_procurador.get(url, {"situacao": Situacao.SUSPENSO}).context
    assert [e.numero_processo for e in filtrado["execucoes"]] == ["0000001-00.2020.8.16.0001"]
    assert filtrado["totais"]["valor"] == Decimal("100.00")

    ordenado = cliente_procurador.get(url, {"ordem": "-valor"}).context["execucoes"]
    assert [e.valor_executado for e in ordenado] == [Decimal("250.50"), Decimal("100.00")]

    parcial = cliente_procurador.get(url, {"acao": "1"}, headers={"HX-Request": "true"})
    assert parcial.templates[0].name == "empresas/_tabela.html"
    assert len(parcial.context["execucoes"]) == 1


def test_exportacao_csv_e_pdf(cliente_procurador, empresa):
    ExecucaoFiscal.objects.create(
        empresa=empresa, numero_processo=NUMERO, valor_executado=Decimal("1234.56"),
        cdas=["CDA-1"], apropriacoes=[{"descricao": "Valor", "protocolo_sefa": "2022/1"}],
        revisado_manualmente=True, campos_revisados=["cdas"],
    )  # fmt: skip
    resposta = cliente_procurador.get(reverse("empresas:exportar", args=[empresa.pk, "csv"]))
    conteudo = resposta.content.decode("utf-8-sig")
    linhas = list(csv.reader(io.StringIO(conteudo), delimiter=";"))
    assert linhas[1] == [settings.AVISO_IA]
    assert linhas[3][0] == NUMERO
    assert linhas[3][2] == "1234,56"
    assert "protocolo SEFA: 2022/1" in linhas[3][4]
    assert linhas[3][8] == "cdas"

    pdf = cliente_procurador.get(reverse("empresas:exportar", args=[empresa.pk, "pdf"]))
    assert pdf["Content-Type"] == "application/pdf"
    texto = " ".join(
        " ".join(p.extract_text().split()) for p in pypdf.PdfReader(io.BytesIO(pdf.content)).pages
    )
    assert "Tabela consolidada de execuções fiscais" in texto
    assert NUMERO in texto
    assert "R$ 1.234,56" in texto
    assert LogAuditoria.objects.filter(acao=Acao.EXPORTACAO).count() == 2
    assert (
        cliente_procurador.get(reverse("empresas:exportar", args=[empresa.pk, "xls"])).status_code
        == 404
    )


# --- documentos que excedem o contexto do modelo --------------------------------------


def test_mesclar_combina_blocos_dos_mesmos_autos():
    inicio = consolidacao.DadosExecucao(
        numero_processo=NUMERO, cdas=["CDA-1"], valor_executado=Decimal("100"),
        teses_defesa=["Prescrição"], situacao=Situacao.CUMPRIMENTO, situacao_detalhe="Penhora",
    )  # fmt: skip
    meio = consolidacao.DadosExecucao(
        numero_processo=NUMERO, cdas=["CDA-1", "CDA-2"], valor_executado=Decimal("999"),
        apropriacoes=[{"descricao": "Valor", "protocolo_sefa": "2022/1"}],
    )  # fmt: skip
    fim = consolidacao.DadosExecucao(
        numero_processo=NUMERO, teses_defesa=["Prescrição", "Nulidade da CDA"],
        situacao=Situacao.SUSPENSO, situacao_detalhe="Art. 40", acao_imediata=True,
    )  # fmt: skip
    dados = consolidacao.mesclar([inicio, meio, fim])
    assert dados.cdas == ["CDA-1", "CDA-2"]
    assert dados.valor_executado == Decimal("100")  # o da petição inicial
    assert dados.teses_defesa == ["Prescrição", "Nulidade da CDA"]
    assert dados.apropriacoes == [{"descricao": "Valor", "protocolo_sefa": "2022/1"}]
    assert (dados.situacao, dados.situacao_detalhe, dados.acao_imediata) == (
        Situacao.SUSPENSO, "Art. 40", True,
    )  # fmt: skip


def test_extracao_divide_autos_extensos_em_blocos(agentes, monkeypatch):
    from apps.provedores import services as ia

    tarefas = []
    original = ia.gerar

    def espiao(modelo, system_prompt, user_content, **opts):
        tarefas.append(opts.get("tarefa"))
        return original(modelo, system_prompt, user_content, **opts)

    monkeypatch.setattr(ia, "gerar", espiao)
    folha = "\n".join(CABECALHO + MOVIMENTACOES)
    texto = "\n\n".join(f"--- [fl. {i}] ---\n{folha}" for i in range(1, 41))
    dados = consolidacao.extrair_dados(agentes["extracao-estruturada"], texto)

    assert tarefas.count("extracao") > 1  # modelo de demonstração: contexto pequeno
    assert dados.numero_processo == NUMERO
    assert dados.cdas == ["20210001234-5"]
    assert dados.valor_executado == Decimal("150000.00")
    assert dados.situacao == Situacao.AGUARDANDO_MANIFESTACAO
