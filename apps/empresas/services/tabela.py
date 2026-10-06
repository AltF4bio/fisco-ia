"""Consulta, totais e exportação (CSV e PDF) da tabela consolidada."""

from __future__ import annotations

import csv
import io
from dataclasses import dataclass
from decimal import Decimal

from django.conf import settings
from django.db.models import Count, QuerySet, Sum
from django.utils import timezone
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, Spacer

from apps.core import pdf
from apps.core.templatetags.fisco import moeda
from apps.empresas.models import Empresa, ExecucaoFiscal, Situacao

ORDENACOES = {
    "numero": "numero_processo",
    "valor": "valor_executado",
    "situacao": "situacao",
    "atualizacao": "ultima_atualizacao",
    "acao": "acao_imediata",
}


@dataclass(frozen=True)
class Filtros:
    situacao: str = ""
    somente_acao: bool = False
    busca: str = ""
    ordem: str = "-acao"

    @classmethod
    def de_query(cls, query) -> Filtros:
        situacao = query.get("situacao", "")
        ordem = query.get("ordem", "-acao")
        return cls(
            situacao=situacao if situacao in Situacao.values else "",
            somente_acao=query.get("acao") == "1",
            busca=query.get("busca", "").strip()[:30],
            ordem=ordem if ordem.lstrip("-") in ORDENACOES else "-acao",
        )


def consultar(empresa: Empresa, filtros: Filtros) -> QuerySet[ExecucaoFiscal]:
    qs = empresa.execucoes.all()
    if filtros.situacao:
        qs = qs.filter(situacao=filtros.situacao)
    if filtros.somente_acao:
        qs = qs.filter(acao_imediata=True)
    if filtros.busca:
        qs = qs.filter(numero_processo__icontains=filtros.busca)
    campo = ORDENACOES[filtros.ordem.lstrip("-")]
    prefixo = "-" if filtros.ordem.startswith("-") else ""
    return qs.order_by(f"{prefixo}{campo}", "numero_processo")


def totais(qs: QuerySet[ExecucaoFiscal]) -> dict:
    agregado = qs.aggregate(quantidade=Count("id"), valor=Sum("valor_executado"))
    return {
        "quantidade": agregado["quantidade"],
        "valor": agregado["valor"] or Decimal("0"),
        "acao_imediata": qs.filter(acao_imediata=True).count(),
    }


def _apropriacoes_texto(execucao: ExecucaoFiscal) -> list[str]:
    return [
        f"{a.get('descricao', '')} (protocolo SEFA: {a.get('protocolo_sefa') or 'não informado'})"
        for a in execucao.apropriacoes
    ]


def _linha(execucao: ExecucaoFiscal) -> list[str]:
    return [
        execucao.numero_processo,
        "; ".join(execucao.cdas),
        f"{execucao.valor_executado:.2f}".replace(".", ",") if execucao.valor_executado else "",
        "; ".join(execucao.bens_penhorados),
        "; ".join(_apropriacoes_texto(execucao)),
        "; ".join(execucao.teses_defesa),
        execucao.get_situacao_display()
        + (f" — {execucao.situacao_detalhe}" if execucao.situacao_detalhe else ""),
        "Sim" if execucao.acao_imediata else "Não",
        ", ".join(execucao.campos_revisados) if execucao.revisado_manualmente else "Não",
        timezone.localtime(execucao.ultima_atualizacao).strftime("%d/%m/%Y %H:%M"),
    ]


CABECALHO = [
    "Número do processo",
    "CDA(s)",
    "Valor executado (R$)",
    "Bens penhorados",
    "Apropriações (protocolo SEFA)",
    "Teses de defesa",
    "Situação processual",
    "Ação imediata",
    "Revisado pelo procurador",
    "Última atualização",
]


def exportar_csv(empresa: Empresa, qs: QuerySet[ExecucaoFiscal]) -> str:
    """CSV em UTF-8 com BOM e separador ';' (abre corretamente no Excel em pt-BR)."""
    saida = io.StringIO()
    escritor = csv.writer(saida, delimiter=";")
    escritor.writerow([f"FISCO.IA — {empresa.razao_social} ({empresa.cnpj_formatado})"])
    escritor.writerow([settings.AVISO_IA])
    escritor.writerow(CABECALHO)
    escritor.writerows(_linha(e) for e in qs)
    return "﻿" + saida.getvalue()


def exportar_pdf(empresa: Empresa, qs: QuerySet[ExecucaoFiscal], filtros: Filtros) -> bytes:
    estilos = pdf.estilos()
    resumo = totais(qs)
    largura = pdf.largura_util(paisagem=True)
    descricao_filtro = []
    if filtros.situacao:
        descricao_filtro.append(f"situação: {Situacao(filtros.situacao).label}")
    if filtros.somente_acao:
        descricao_filtro.append("somente ação imediata")
    if filtros.busca:
        descricao_filtro.append(f"busca: {filtros.busca}")
    metadados = [
        ("Empresa", f"{empresa.razao_social} — CNPJ {empresa.cnpj_formatado}"),
        ("Execuções listadas", str(resumo["quantidade"])),
        ("Valor executado somado", moeda(resumo["valor"])),
        ("Demandam ação imediata", str(resumo["acao_imediata"])),
        ("Filtros", ", ".join(descricao_filtro) or "nenhum"),
        ("Gerado em", timezone.localtime().strftime("%d/%m/%Y %H:%M")),
    ]
    colunas = [c for i, c in enumerate(CABECALHO) if i != 9]
    linhas = [colunas] + [[c for i, c in enumerate(_linha(e)) if i != 9] for e in qs]
    proporcoes = [19, 9, 8, 13, 14, 10, 13, 5, 9]
    larguras = [largura * p / sum(proporcoes) for p in proporcoes]
    elementos = [
        pdf.tabela_metadados(metadados, largura),
        pdf.bloco_aviso_ia(),
        Paragraph(
            "Linhas marcadas como revisadas tiveram campos corrigidos manualmente pelo "
            "procurador; a revisão humana prevalece sobre a extração automática.",
            estilos["rodape"],
        ),
        Spacer(1, 3 * mm),
        pdf.tabela(linhas, larguras) if qs else Paragraph("Nenhuma execução.", estilos["corpo"]),
    ]
    return pdf.gerar_pdf("Tabela consolidada de execuções fiscais", elementos, paisagem=True)
