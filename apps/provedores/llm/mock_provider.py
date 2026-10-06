"""MockProvider: respostas determinísticas para demonstração e testes.

Não faz nenhuma chamada externa. As respostas são montadas por heurísticas simples
sobre o próprio texto enviado (movimentações, datas, CDAs, penhoras), de modo que a
demonstração reflita o documento analisado. Não substitui um modelo de linguagem.
"""

from __future__ import annotations

import json
import re
from typing import Any

from apps.provedores.llm.base import LLMProvider, LLMResult
from apps.provedores.llm.tarefas import Tarefa

RE_MOVIMENTACAO = re.compile(
    r"Mov(?:imenta[çc][ãa]o|\.)?\s*(?:n[ºo°.]\s*)?(\d{1,4})\s*[-–—:]\s*(\d{2}/\d{2}/\d{4})\s*[-–—:]\s*(.+)",
    re.IGNORECASE,
)
RE_PROCESSO = re.compile(r"\b\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}\b")
RE_CDA = re.compile(r"CDA\s*(?:n[ºo°.]\s*)?([\d./-]{5,})", re.IGNORECASE)
RE_VALOR = re.compile(
    r"(?:valor\s+(?:da\s+causa|executado|do\s+d[ée]bito|atualizado)[^R]{0,30})R\$\s*([\d.]+,\d{2})",
    re.IGNORECASE,
)
RE_PROTOCOLO_SEFA = re.compile(r"protocolo\s+(?:SEFA\s*)?(?:n[ºo°.]\s*)?([\d./-]{5,})", re.I)
RE_ESCLARECIMENTOS = re.compile(r"ESCLARECIMENTOS DO PROCURADOR\s*(.+)", re.DOTALL)

TERMOS_ESCOPO = (
    "execução fiscal",
    "lei 6.830",
    "lei nº 6.830",
    "certidão de dívida ativa",
    "cda",
    "fazenda pública",
    "dívida ativa",
)
MARCADORES_LACUNA = {
    "ilegível": "há trecho registrado como ilegível",
    "não juntad": "há referência a documento não juntado aos autos",
    "não consta": "há informação que não consta dos autos",
}
TESES = {
    "prescrição": "Prescrição",
    "prescricao": "Prescrição",
    "nulidade da cda": "Nulidade da CDA",
    "fato gerador": "Ausência de fato gerador",
    "ilegitimidade passiva": "Ilegitimidade passiva",
    "dissolução irregular": "Dissolução irregular",
    "excesso de execução": "Excesso de execução",
    "decadência": "Decadência",
}
TERMOS_DECISAO = ("decisão", "sentença", "acórdão", "despacho", "decido", "julgo")
TERMOS_PENHORA = ("penhora", "bloqueio", "sisbajud", "renajud", "arresto", "apropria")
SITUACOES = (
    ("arquivad", "encerrado"),
    ("extint", "encerrado"),
    ("suspens", "suspenso"),
    ("apelação", "recurso_pendente"),
    ("agravo", "recurso_pendente"),
    ("embargos", "aguardando_manifestacao"),
    ("intime-se a fazenda", "aguardando_manifestacao"),
    ("penhora", "cumprimento"),
)


class MockProvider(LLMProvider):
    """Provedor de demonstração: determinístico e sem custo."""

    nome = "mock"

    def generate(self, system_prompt: str, user_content: str, model: str, **opts: Any) -> LLMResult:
        tarefa = opts.get("tarefa", Tarefa.ANALISE)
        gerador = {
            Tarefa.ESCOPO: self._escopo,
            Tarefa.PERGUNTAS: self._perguntas,
            Tarefa.EXTRACAO: self._extracao,
            Tarefa.CONSOLIDACAO: self._consolidacao,
        }.get(tarefa)
        if gerador is not None:
            texto = gerador(user_content)
        else:
            texto = self._analise(user_content, opts.get("agente", ""))
        return LLMResult(
            texto=texto,
            provedor=self.nome,
            modelo=model,
            tokens_entrada=len(system_prompt + user_content) // 4,
            tokens_saida=len(texto) // 4,
        )

    def testar_conexao(self) -> str:
        return "Provedor de demonstração ativo (nenhuma chamada externa é realizada)."

    # --- tarefas auxiliares ---------------------------------------------------

    def _escopo(self, conteudo: str) -> str:
        baixo = conteudo.lower()
        encontrados = [t for t in TERMOS_ESCOPO if t in baixo]
        eh_execucao = len(encontrados) >= 2
        justificativa = (
            f"O documento contém elementos típicos de execução fiscal ({', '.join(encontrados)})."
            if eh_execucao
            else "O documento não apresenta elementos característicos de execução fiscal."
        )
        return json.dumps({"execucao_fiscal": eh_execucao, "justificativa": justificativa})

    def _perguntas(self, conteudo: str) -> str:
        perguntas = []
        for numero, data, descricao in _movimentacoes(conteudo):
            baixo = descricao.lower()
            for marcador, motivo in MARCADORES_LACUNA.items():
                if marcador in baixo:
                    perguntas.append(
                        {
                            "id": f"p{len(perguntas) + 1}",
                            "pergunta": (
                                f"Na movimentação {numero} ({data}), {motivo}. "
                                "O procurador dispõe dessa informação? Se sim, descreva-a."
                            ),
                            "referencia": f"Mov. {numero}",
                        }
                    )
        return json.dumps({"perguntas": perguntas[:5]}, ensure_ascii=False)

    def _extracao(self, conteudo: str) -> str:
        movimentacoes = _movimentacoes(conteudo)
        processo = RE_PROCESSO.search(conteudo)
        valor = RE_VALOR.search(conteudo)
        bens = [
            f"Mov. {n} ({d}): {desc}"
            for n, d, desc in movimentacoes
            if "penhora" in desc.lower() and "apropria" not in desc.lower()
        ]
        apropriacoes = [
            {
                "descricao": f"Mov. {n} ({d}): {desc}",
                "protocolo_sefa": (
                    m.group(1).rstrip(".") if (m := RE_PROTOCOLO_SEFA.search(desc)) else ""
                ),
            }
            for n, d, desc in movimentacoes
            if "apropria" in desc.lower()
        ]
        dados = {
            "numero_processo": processo.group(0) if processo else "",
            "cdas": sorted({c.rstrip(".") for c in RE_CDA.findall(conteudo)}),
            "valor_executado": valor.group(1).replace(".", "").replace(",", ".") if valor else None,
            "bens_penhorados": bens,
            "apropriacoes": apropriacoes,
            "teses_defesa": _teses(conteudo),
            "situacao": _situacao(movimentacoes),
            "situacao_detalhe": _resumo_ultima(movimentacoes),
            "acao_imediata": _exige_acao(movimentacoes),
        }
        return json.dumps(dados, ensure_ascii=False)

    def _consolidacao(self, conteudo: str) -> str:
        vistas: set[str] = set()
        linhas = []
        for linha in conteudo.splitlines():
            chave = linha.strip()
            if chave.startswith("=== ANÁLISE PARCIAL") or (chave and chave in vistas):
                continue
            vistas.add(chave)
            linhas.append(linha)
        corpo = "\n".join(linhas).strip()
        return f"{corpo}\n\n_Consolidação de análises parciais de blocos do documento._"

    # --- análises por agente --------------------------------------------------

    def _analise(self, conteudo: str, agente: str) -> str:
        movimentacoes = _movimentacoes(conteudo)
        esclarecimentos = RE_ESCLARECIMENTOS.search(conteudo)
        geradores = {
            "resumo-cronologico": _cronologico,
            "sintese-decisoes": _decisoes,
            "penhora-apropriacao": _penhora,
            "fundamentos-juridicos": lambda m: _fundamentos(conteudo),
            "diagnostico-situacao": _diagnostico,
        }
        corpo = geradores.get(agente, _cronologico)(movimentacoes)
        if esclarecimentos:
            corpo += (
                "\n\n### Esclarecimentos do procurador considerados\n\n"
                + esclarecimentos.group(1).strip()
            )
        return corpo


def _movimentacoes(texto: str) -> list[tuple[str, str, str]]:
    return [(m.group(1), m.group(2), m.group(3).strip()) for m in RE_MOVIMENTACAO.finditer(texto)]


def _cronologico(movs: list[tuple[str, str, str]]) -> str:
    if not movs:
        return "Não foram identificadas movimentações numeradas no documento."
    linhas = ["## Linha do tempo do processo", "", "| Mov. | Data | Evento |", "|---|---|---|"]
    linhas += [f"| {n} | {d} | {_curto(desc)} |" for n, d, desc in movs]
    return "\n".join(linhas)


def _decisoes(movs: list[tuple[str, str, str]]) -> str:
    achadas = [m for m in movs if any(t in m[2].lower() for t in TERMOS_DECISAO)]
    if not achadas:
        return "Não constam dos autos decisões interlocutórias, sentenças ou acórdãos."
    linhas = ["## Decisões identificadas", ""]
    for n, d, desc in achadas:
        tipo = next((t.capitalize() for t in TERMOS_DECISAO if t in desc.lower()), "Decisão")
        linhas.append(f"- **{tipo} — Mov. {n} ({d})**: {_curto(desc, 220)}")
    return "\n".join(linhas)


def _penhora(movs: list[tuple[str, str, str]]) -> str:
    achadas = [m for m in movs if any(t in m[2].lower() for t in TERMOS_PENHORA)]
    if not achadas:
        return "Não constam dos autos penhoras, bloqueios ou apropriações de bens."
    linhas = ["## Bens penhorados e apropriações", ""]
    for n, d, desc in achadas:
        protocolo = RE_PROTOCOLO_SEFA.search(desc)
        sufixo = (
            f" — protocolo SEFA **{protocolo.group(1).rstrip('.')}**"
            if protocolo
            else (" — protocolo SEFA não informado nos autos" if "apropria" in desc.lower() else "")
        )
        linhas.append(f"- Mov. {n} ({d}): {_curto(desc, 220)}{sufixo}")
    return "\n".join(linhas)


def _fundamentos(texto: str) -> str:
    teses = _teses(texto)
    if not teses:
        return "Não constam dos autos teses de defesa (embargos, exceções ou recursos)."
    linhas = ["## Teses alegadas pela parte executada", ""]
    linhas += [f"- **{tese}** — alegação identificada no documento." for tese in teses]
    return "\n".join(linhas)


def _diagnostico(movs: list[tuple[str, str, str]]) -> str:
    if not movs:
        return "Não foi possível determinar a situação processual: não há movimentações legíveis."
    rotulos = {
        "encerrado": "encerrado",
        "suspenso": "suspenso",
        "recurso_pendente": "com recurso pendente",
        "aguardando_manifestacao": "aguardando manifestação",
        "cumprimento": "em fase de cumprimento (atos de constrição)",
        "em_andamento": "em andamento",
    }
    n, d, desc = movs[-1]
    return (
        f"## Diagnóstico\n\nO processo encontra-se **{rotulos[_situacao(movs)]}**. A última "
        f"movimentação registrada é a de nº {n}, de {d}: {_curto(desc, 200)}."
    )


def _teses(texto: str) -> list[str]:
    baixo = texto.lower()
    return sorted({rotulo for termo, rotulo in TESES.items() if termo in baixo})


def _situacao(movs: list[tuple[str, str, str]]) -> str:
    for _, _, desc in reversed(movs[-3:]):
        baixo = desc.lower()
        for termo, situacao in SITUACOES:
            if termo in baixo:
                return situacao
    return "em_andamento"


def _exige_acao(movs: list[tuple[str, str, str]]) -> bool:
    if not movs:
        return False
    baixo = movs[-1][2].lower()
    return any(
        t in baixo for t in ("intime-se a fazenda", "prazo", "manifeste-se", "vista à fazenda")
    )


def _resumo_ultima(movs: list[tuple[str, str, str]]) -> str:
    if not movs:
        return ""
    n, d, desc = movs[-1]
    return f"Última movimentação: Mov. {n} ({d}) — {_curto(desc, 160)}"


def _curto(texto: str, limite: int = 140) -> str:
    texto = " ".join(texto.split())
    return texto if len(texto) <= limite else texto[: limite - 1].rstrip() + "…"
