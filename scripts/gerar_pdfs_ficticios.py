"""Gera PDFs FICTÍCIOS para demonstração e testes manuais do FISCO.IA.

Todos os nomes, números de processo, CNPJs, CDAs, valores e protocolos são
inventados. Os documentos não reproduzem layout ou identidade visual de nenhum
tribunal ou sistema oficial.

Uso:
    python scripts/gerar_pdfs_ficticios.py [pasta_de_saida]   # padrão: exemplos/
"""

from __future__ import annotations

import sys
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer

AVISO = "DOCUMENTO FICTÍCIO — DADOS INVENTADOS PARA DEMONSTRAÇÃO ACADÊMICA (FISCO.IA)"
EMPRESA = "METALÚRGICA HORIZONTE FICTÍCIA LTDA."
CNPJ = "45.723.174/0001-10"

_base = getSampleStyleSheet()
TITULO = ParagraphStyle("t", parent=_base["Title"], fontSize=13, leading=16)
NORMAL = ParagraphStyle("n", parent=_base["BodyText"], fontSize=9.5, leading=13)
MOV = ParagraphStyle("m", parent=NORMAL, fontName="Helvetica-Bold", spaceBefore=6)
CORPO = ParagraphStyle("c", parent=NORMAL, leftIndent=12, textColor=colors.HexColor("#333333"))


def _moldura(c: canvas.Canvas, doc) -> None:
    c.saveState()
    c.setFont("Helvetica-Bold", 7.5)
    c.setFillColor(colors.HexColor("#9a3412"))
    c.drawCentredString(A4[0] / 2, A4[1] - 10 * mm, AVISO)
    c.setFillColor(colors.grey)
    c.setFont("Helvetica", 7.5)
    c.drawRightString(A4[0] - 15 * mm, 10 * mm, f"fl. {doc.page}")
    c.restoreState()


def _cabecalho(numero: str, cdas: str, valor: str, assunto: str) -> list:
    return [
        Paragraph("EXTRATO DE MOVIMENTAÇÕES PROCESSUAIS", TITULO),
        Paragraph(
            "Vara de Execuções Fiscais Estaduais da Comarca Fictícia de Vale Azul — PR", NORMAL
        ),
        Spacer(1, 4),
        Paragraph(f"<b>Processo:</b> EXECUÇÃO FISCAL nº {numero}", NORMAL),
        Paragraph("<b>Classe:</b> Execução Fiscal (Lei nº 6.830/80)", NORMAL),
        Paragraph(f"<b>Assunto:</b> {assunto}", NORMAL),
        Paragraph("<b>Exequente:</b> ESTADO DO PARANÁ — Fazenda Pública Estadual", NORMAL),
        Paragraph(f"<b>Executada:</b> {EMPRESA} — CNPJ {CNPJ}", NORMAL),
        Paragraph(f"<b>Certidões de Dívida Ativa:</b> {cdas}", NORMAL),
        Paragraph(f"<b>Valor da causa:</b> R$ {valor}", NORMAL),
        Spacer(1, 8),
    ]


def _movimentacoes(itens: list[tuple[str, str, str]]) -> list:
    elementos = []
    for numero, (data, titulo, corpo) in enumerate(itens, 1):
        elementos.append(Paragraph(f"Mov. {numero} - {data} - {titulo}", MOV))
        if corpo:
            elementos.append(Paragraph(corpo, CORPO))
    return elementos


def _salvar(destino: Path, elementos: list) -> None:
    doc = SimpleDocTemplate(
        str(destino), pagesize=A4, topMargin=18 * mm, bottomMargin=18 * mm,
        leftMargin=18 * mm, rightMargin=18 * mm, title=destino.stem, author="FISCO.IA (fictício)",
    )  # fmt: skip
    doc.build(elementos, onFirstPage=_moldura, onLaterPages=_moldura)


def execucao_interativa(destino: Path) -> None:
    """Execução com lacunas (trecho ilegível, documento não juntado): aciona o modo interativo."""
    itens = [
        ("12/03/2019", "Distribuída a petição inicial de execução fiscal",
         "A Fazenda Pública do Estado do Paraná ajuíza execução fiscal para cobrança de ICMS "
         "declarado e não pago, inscrito nas CDAs nº 2018/0045123-7 e nº 2018/0045124-5."),
        ("20/03/2019", "Despacho: cite-se a executada para pagar ou garantir a execução em 5 dias",
         "Cite-se nos termos do art. 8º da Lei 6.830/80."),
        ("14/05/2019", "Juntada de aviso de recebimento — citação positiva", ""),
        ("03/07/2019", "Decisão: deferido o bloqueio de ativos financeiros via SISBAJUD", ""),
        ("18/07/2019", "Penhora de ativos financeiros via SISBAJUD no valor de R$ 32.410,55",
         "Valor transferido para conta judicial vinculada ao juízo."),
        ("02/09/2019", "Exceção de pré-executividade alegando prescrição",
         "A executada sustenta a ocorrência de prescrição dos créditos de 2013, pois a "
         "constituição definitiva teria ocorrido há mais de cinco anos do despacho citatório."),
        ("30/10/2019", "Manifestação da Fazenda Pública rejeitando a alegação de prescrição", ""),
        ("05/02/2020", "Decisão: rejeitada a exceção de pré-executividade",
         "Não se verifica a prescrição, pois a declaração do contribuinte foi entregue em 2014 e "
         "o despacho citatório interrompeu o prazo (art. 174, parágrafo único, I, do CTN)."),
        ("11/03/2020", "Penhora de imóvel (matrícula nº 98.765) — auto com trecho ilegível",
         "Imóvel industrial avaliado em R$ 610.000,00. A descrição das benfeitorias no auto de "
         "penhora está ilegível em razão de digitalização deficiente."),
        ("22/04/2020", "Embargos à execução; laudo contábil citado e não juntado aos autos",
         "A embargante alega nulidade da CDA, por ausência de fundamentação legal, e excesso de "
         "execução, por cobrança de multa confiscatória, com base em laudo contábil não juntado."),
        ("15/09/2020", "Impugnação aos embargos apresentada pela Fazenda Pública", ""),
        ("09/06/2021", "Sentença: julgo improcedentes os embargos à execução",
         "A CDA preenche os requisitos do art. 2º, § 5º, da Lei 6.830/80; a multa observa a "
         "legislação estadual vigente."),
        ("01/08/2021", "Apropriação de valores pelo Estado do Paraná, protocolo SEFA nº 2021/0387741",
         "Conversão em renda do depósito SISBAJUD de R$ 32.410,55 em favor do Estado do Paraná."),
        ("20/10/2021", "Apelação interposta pela executada", ""),
        ("08/11/2021", "Intime-se a Fazenda Pública para apresentar contrarrazões em 30 dias", ""),
    ]  # fmt: skip
    _salvar(
        destino,
        _cabecalho(
            "0004567-89.2019.8.16.0014",
            "CDA nº 2018/0045123-7 e CDA nº 2018/0045124-5",
            "487.352,19",
            "ICMS — imposto declarado e não pago",
        )
        + _movimentacoes(itens),
    )


def execucao_extensa(destino: Path) -> None:
    """Execução longa: excede o contexto do modelo de demonstração e aciona o map-reduce."""
    itens = [
        ("10/05/2017", "Distribuída a petição inicial de execução fiscal",
         "Cobrança de ICMS-ST inscrito na CDA nº 2016/0011223-9."),
        ("16/05/2017", "Despacho: cite-se a executada", ""),
        ("30/06/2017", "Certidão do oficial de justiça: executada não localizada no endereço", ""),
        ("12/09/2017", "Petição da Fazenda Pública requerendo citação por edital", ""),
        ("20/10/2017", "Decisão: deferida a citação por edital", ""),
    ]  # fmt: skip
    rotina = [
        "Juntada de petição intermediária da Fazenda Pública",
        "Certidão de decurso de prazo",
        "Juntada de ofício de instituição financeira com resposta negativa",
        "Pesquisa RENAJUD sem veículos localizados",
        "Pesquisa de bens imóveis com resultado negativo",
        "Vista à Fazenda Pública para indicar bens",
        "Petição da Fazenda requerendo nova pesquisa SISBAJUD",
        "Decisão: deferida nova pesquisa SISBAJUD",
        "Resultado SISBAJUD: bloqueio de valor irrisório, desbloqueado",
    ]
    detalhe = (
        "Ato processual registrado no sistema com a respectiva certidão. Não houve alteração "
        "relevante na marcha processual, permanecendo a execução sem garantia do juízo. "
        "A serventia certifica a regularidade das intimações eletrônicas efetuadas."
    )
    for i in range(60):
        ano, mes = 2018 + i // 12, i % 12 + 1
        itens.append((f"{(i % 27) + 1:02d}/{mes:02d}/{ano}", rotina[i % len(rotina)], detalhe))
    itens += [
        ("15/02/2023", "Decisão: suspensão do processo nos termos do art. 40 da Lei 6.830/80",
         "Não localizados bens penhoráveis, suspende-se o curso da execução por um ano."),
        ("20/02/2024", "Certidão: arquivamento provisório (art. 40, § 2º) — processo suspenso",
         "Decorrido o prazo de um ano sem localização de bens (Lei 6.830/80)."),
    ]  # fmt: skip
    _salvar(
        destino,
        _cabecalho(
            "0012890-33.2017.8.16.0004",
            "CDA nº 2016/0011223-9",
            "128.904,77",
            "ICMS — substituição tributária",
        )
        + _movimentacoes(itens),
    )


def execucao_digitalizada(destino: Path) -> None:
    """Simula autos digitalizados sem OCR: quase nenhum texto extraível."""
    c = canvas.Canvas(str(destino), pagesize=A4)
    c.setTitle(destino.stem)
    c.setFont("Helvetica-Bold", 8)
    c.drawString(20 * mm, A4[1] - 15 * mm, AVISO)
    c.setFont("Helvetica", 10)
    c.drawString(20 * mm, A4[1] - 25 * mm, "EXECUÇÃO FISCAL nº 0007788-12.2020.8.16.0021")
    c.drawString(
        20 * mm, A4[1] - 31 * mm, "Fazenda Pública do Estado do Paraná — CDA nº 2019/0099887-1"
    )
    c.showPage()
    for pagina in range(4):
        c.setFillColor(colors.HexColor("#d9d4c7"))
        c.rect(15 * mm, 15 * mm, A4[0] - 30 * mm, A4[1] - 30 * mm, stroke=0, fill=1)
        c.setFillColor(colors.HexColor("#8c867a"))
        for linha in range(38):
            largura = (A4[0] - 50 * mm) * (0.55 + 0.4 * ((linha * 7 + pagina) % 5) / 5)
            c.rect(25 * mm, A4[1] - 30 * mm - linha * 6.5 * mm, largura, 2.2 * mm, stroke=0, fill=1)
        c.showPage()
    c.save()


def documento_nao_fiscal(destino: Path) -> None:
    """Contrato privado: deve ser recusado pela verificação de escopo."""
    clausulas = [
        "CONTRATANTE: Padaria Pão Dourado Fictícia Ltda. CONTRATADA: Sistemas Exemplo Ltda.",
        "Cláusula 1ª — Objeto: prestação de serviços de manutenção de software de frente de caixa.",
        "Cláusula 2ª — Preço: R$ 1.200,00 mensais, com vencimento todo dia 10.",
        "Cláusula 3ª — Vigência: 12 meses, renováveis por acordo entre as partes.",
        "Cláusula 4ª — Rescisão: qualquer parte pode rescindir com aviso prévio de 30 dias.",
        "Cláusula 5ª — Foro: fica eleito o foro da Comarca Fictícia de Vale Azul — PR.",
    ]
    _salvar(
        destino,
        [Paragraph("CONTRATO DE PRESTAÇÃO DE SERVIÇOS", TITULO), Spacer(1, 6)]
        + [Paragraph(c, NORMAL) for c in clausulas]
        + [
            PageBreak(),
            Paragraph("Vale Azul — PR, 3 de março de 2025. Assinaturas das partes.", NORMAL),
        ],
    )


GERADORES = {
    "execucao_fiscal_01_modo_interativo.pdf": execucao_interativa,
    "execucao_fiscal_02_extensa_map_reduce.pdf": execucao_extensa,
    "execucao_fiscal_03_digitalizada_sem_ocr.pdf": execucao_digitalizada,
    "documento_fora_do_escopo.pdf": documento_nao_fiscal,
}


def main() -> None:
    saida = Path(sys.argv[1] if len(sys.argv) > 1 else "exemplos")
    saida.mkdir(parents=True, exist_ok=True)
    for nome, gerar in GERADORES.items():
        gerar(saida / nome)
        sys.stdout.write(f"Gerado: {saida / nome}\n")


if __name__ == "__main__":
    main()
