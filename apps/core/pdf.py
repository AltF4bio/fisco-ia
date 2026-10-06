"""Geração de PDFs do FISCO.IA com reportlab (sem dependências de sistema).

Todas as páginas trazem o cabeçalho "FISCO.IA — protótipo acadêmico" e, no rodapé,
o aviso institucional sobre conteúdo gerado por inteligência artificial.
"""

from __future__ import annotations

import io
import re
from collections.abc import Iterable
from xml.sax.saxutils import escape

from django.conf import settings
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    Flowable,
    KeepTogether,
    ListFlowable,
    ListItem,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

AZUL = colors.HexColor("#0b2545")
AZUL_CLARO = colors.HexColor("#dde6f0")
CINZA = colors.HexColor("#5b6472")
AMARELO = colors.HexColor("#fff8e6")
MARGEM = 18 * mm
RODAPE_ACADEMICO = (
    "Protótipo acadêmico — TCC Sistemas de Informação, UNIPAR 2026. "
    "Não é um sistema oficial da PGE-PR."
)


def estilos() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "titulo": ParagraphStyle("titulo", parent=base["Title"], fontSize=15, textColor=AZUL,
                                 alignment=TA_LEFT, spaceAfter=6),
        "h1": ParagraphStyle("h1", parent=base["Heading2"], fontSize=12.5, textColor=AZUL,
                             spaceBefore=8, spaceAfter=4),
        "h2": ParagraphStyle("h2", parent=base["Heading3"], fontSize=11, textColor=AZUL,
                             spaceBefore=6, spaceAfter=3),
        "corpo": ParagraphStyle("corpo", parent=base["BodyText"], fontSize=10, leading=14),
        "celula": ParagraphStyle("celula", parent=base["BodyText"], fontSize=8.5, leading=10.5),
        "celula_cab": ParagraphStyle("celula_cab", parent=base["BodyText"], fontSize=8.5,
                                     leading=10.5, textColor=colors.white,
                                     fontName="Helvetica-Bold"),
        "rodape": ParagraphStyle("rodape", parent=base["BodyText"], fontSize=7.5, leading=9,
                                 textColor=CINZA),
        "aviso": ParagraphStyle("aviso", parent=base["BodyText"], fontSize=9, leading=12,
                                textColor=colors.HexColor("#5c4100"), backColor=AMARELO,
                                borderColor=colors.HexColor("#b58105"), borderWidth=0.6,
                                borderPadding=6, spaceBefore=12, spaceAfter=12),
    }  # fmt: skip


def inline(texto: str) -> str:
    """Escapa o texto e converte **negrito**, *itálico* e `código` em marcação do reportlab."""
    texto = escape(texto)
    texto = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", texto)
    texto = re.sub(r"(?<![\w*])[*_](?!\s)(.+?)(?<!\s)[*_](?![\w*])", r"<i>\1</i>", texto)
    return re.sub(r"`(.+?)`", r"<font face='Courier'>\1</font>", texto)


def larguras_proporcionais(linhas: list[list[str]], largura_total: float) -> list[float]:
    """Distribui a largura conforme o conteúdo de cada coluna (com mínimo e teto)."""
    colunas = max(len(linha) for linha in linhas)
    pesos = [
        min(60, max(6, *(len(linha[i]) if i < len(linha) else 0 for linha in linhas)))
        for i in range(colunas)
    ]
    return [largura_total * peso / sum(pesos) for peso in pesos]


def tabela(linhas: list[list[str]], larguras: list[float] | None = None) -> Table:
    e = estilos()
    larguras = larguras or larguras_proporcionais(linhas, largura_util())
    dados = [
        [Paragraph(inline(c), e["celula_cab"] if i == 0 else e["celula"]) for c in linha]
        for i, linha in enumerate(linhas)
    ]
    t = Table(dados, colWidths=larguras, repeatRows=1, hAlign="LEFT")
    t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), AZUL),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#c4ccd6")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f5f7fa")]),
            ]
        )
    )
    return t


def markdown_para_flowables(texto: str) -> list[Flowable]:
    """Converte o Markdown simples produzido pelos agentes em elementos do PDF."""
    e = estilos()
    elementos: list[Flowable] = []
    paragrafo: list[str] = []
    itens: list[str] = []
    linhas_tabela: list[list[str]] = []

    def fechar() -> None:
        if paragrafo:
            elementos.append(Paragraph(inline(" ".join(paragrafo)), e["corpo"]))
            paragrafo.clear()
        if itens:
            elementos.append(
                ListFlowable(
                    [ListItem(Paragraph(inline(i), e["corpo"]), leftIndent=12) for i in itens],
                    bulletType="bullet",
                    start="•",
                    leftIndent=12,
                )
            )
            itens.clear()
        if linhas_tabela:
            largura = max(len(linha) for linha in linhas_tabela)
            normalizadas = [linha + [""] * (largura - len(linha)) for linha in linhas_tabela]
            elementos.append(tabela(normalizadas))
            elementos.append(Spacer(1, 4))
            linhas_tabela.clear()

    for bruta in texto.splitlines():
        linha = bruta.strip()
        if linha.startswith("|"):
            if paragrafo or itens:
                fechar()
            celulas = [c.strip() for c in linha.strip("|").split("|")]
            if not all(re.fullmatch(r":?-{2,}:?", c) for c in celulas if c):
                linhas_tabela.append(celulas)
            continue
        if linhas_tabela:
            fechar()
        if not linha:
            fechar()
        elif titulo := re.match(r"^(#{1,6})\s+(.*)", linha):
            fechar()
            estilo = e["h1"] if len(titulo.group(1)) <= 2 else e["h2"]
            elementos.append(Paragraph(inline(titulo.group(2)), estilo))
        elif item := re.match(r"^(?:[-*•]|\d+[.)])\s+(.*)", linha):
            if paragrafo:
                fechar()
            itens.append(item.group(1))
        elif itens and bruta.startswith((" ", "\t")):
            itens[-1] += " " + linha
        else:
            if itens:
                fechar()
            paragrafo.append(linha)
    fechar()
    return elementos


def bloco_aviso_ia() -> Paragraph:
    return Paragraph(f"<b>Aviso:</b> {escape(settings.AVISO_IA)}", estilos()["aviso"])


def tabela_metadados(pares: Iterable[tuple[str, str]], largura_total: float) -> Table:
    e = estilos()
    dados = [
        [Paragraph(f"<b>{escape(rotulo)}</b>", e["celula"]), Paragraph(escape(valor), e["celula"])]
        for rotulo, valor in pares
    ]
    t = Table(dados, colWidths=[42 * mm, largura_total - 42 * mm], hAlign="LEFT")
    t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, -1), AZUL_CLARO),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#c4ccd6")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        )
    )
    return t


def gerar_pdf(titulo: str, elementos: list[Flowable], *, paisagem: bool = False) -> bytes:
    """Monta o documento com cabeçalho e rodapé institucionais em todas as páginas."""
    buffer = io.BytesIO()
    tamanho = landscape(A4) if paisagem else A4
    e = estilos()

    def moldura(canvas, doc) -> None:
        largura, altura = tamanho
        canvas.saveState()
        canvas.setFillColor(AZUL)
        canvas.rect(0, altura - 12 * mm, largura, 12 * mm, stroke=0, fill=1)
        canvas.setFillColor(colors.white)
        canvas.setFont("Helvetica-Bold", 10)
        canvas.drawString(MARGEM, altura - 7.8 * mm, "FISCO.IA — protótipo acadêmico")
        canvas.setFont("Helvetica", 8)
        canvas.drawRightString(largura - MARGEM, altura - 7.8 * mm, f"Página {doc.page}")
        rodape = Paragraph(
            f"<b>{escape(settings.AVISO_IA)}</b><br/>{escape(RODAPE_ACADEMICO)}", e["rodape"]
        )
        _, h = rodape.wrap(largura - 2 * MARGEM, 30 * mm)
        canvas.setStrokeColor(colors.HexColor("#c4ccd6"))
        canvas.line(MARGEM, 8 * mm + h + 2, largura - MARGEM, 8 * mm + h + 2)
        rodape.drawOn(canvas, MARGEM, 8 * mm)
        canvas.restoreState()

    documento = SimpleDocTemplate(
        buffer,
        pagesize=tamanho,
        leftMargin=MARGEM,
        rightMargin=MARGEM,
        topMargin=20 * mm,
        bottomMargin=24 * mm,
        title=titulo,
        author="FISCO.IA (protótipo acadêmico)",
    )
    documento.build(
        [KeepTogether([Paragraph(escape(titulo), e["titulo"])]), *elementos],
        onFirstPage=moldura,
        onLaterPages=moldura,
    )
    return buffer.getvalue()


def largura_util(paisagem: bool = False) -> float:
    return (landscape(A4) if paisagem else A4)[0] - 2 * MARGEM
