"""Verificação de escopo: o sistema só analisa processos de execução fiscal.

Combina uma heurística por termos característicos com uma checagem rápida pelo
modelo. Documentos sem nenhum termo característico são recusados sem consultar o
modelo; nos demais casos, prevalece a classificação do modelo (com a heurística
como reserva se a resposta não puder ser interpretada).
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from apps.analises import prompts
from apps.core.json_ia import JSONInvalidoError, ler_objeto_json
from apps.provedores import services as ia
from apps.provedores.llm import Tarefa
from apps.provedores.models import ModeloIA

TERMOS: dict[str, re.Pattern[str]] = {
    "execução fiscal": re.compile(r"execu[çc][ãa]o\s+fiscal", re.I),
    "Lei 6.830/80": re.compile(r"6\.?830(?:/80|/1980|\s+de\s+1980)?", re.I),
    "Certidão de Dívida Ativa": re.compile(r"certid[ãa]o\s+de\s+d[íi]vida\s+ativa", re.I),
    "CDA": re.compile(r"\bCDAs?\b"),
    "Fazenda Pública": re.compile(r"fazenda\s+p[úu]blica", re.I),
    "dívida ativa": re.compile(r"d[íi]vida\s+ativa", re.I),
}
MINIMO_TERMOS_RESERVA = 2
LIMITE_AMOSTRA = 12_000

MENSAGEM_RECUSA = (
    "O documento enviado não foi reconhecido como processo de execução fiscal. "
    "O FISCO.IA é restrito à análise de execuções fiscais (Lei nº 6.830/1980); "
    "documentos de outra natureza não são processados."
)


@dataclass(frozen=True)
class ResultadoEscopo:
    aceito: bool
    termos: list[str]
    justificativa: str
    consultou_modelo: bool


def termos_encontrados(texto: str) -> list[str]:
    return [nome for nome, padrao in TERMOS.items() if padrao.search(texto)]


def verificar(texto: str, modelo: ModeloIA) -> ResultadoEscopo:
    termos = termos_encontrados(texto)
    if not termos:
        return ResultadoEscopo(False, [], "Nenhum termo característico encontrado.", False)

    amostra = texto[:LIMITE_AMOSTRA]
    resposta = ia.gerar(
        modelo,
        prompts.VERIFICACAO_ESCOPO,
        amostra,
        json=True,
        max_tokens=300,
        tarefa=Tarefa.ESCOPO,
    )
    try:
        dados = ler_objeto_json(resposta.texto)
        aceito = bool(dados.get("execucao_fiscal"))
        justificativa = str(dados.get("justificativa", ""))[:300]
    except JSONInvalidoError:
        aceito = len(termos) >= MINIMO_TERMOS_RESERVA
        justificativa = "Classificação do modelo ilegível; aplicada a heurística por termos."
    return ResultadoEscopo(aceito, termos, justificativa, True)
