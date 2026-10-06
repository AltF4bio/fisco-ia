"""Execução da análise pelo agente, com map-reduce quando os autos excedem o contexto."""

from __future__ import annotations

from dataclasses import dataclass

from apps.agentes.models import Agente
from apps.analises import prompts
from apps.analises.services import blocos
from apps.provedores import services as ia
from apps.provedores.llm import LLMResult, Tarefa

# Limite de rodadas de consolidação hierárquica (evita laços em documentos extremos).
MAXIMO_NIVEIS_CONSOLIDACAO = 4


@dataclass(frozen=True)
class ResultadoAnalise:
    texto: str
    provedor: str
    modelo: str
    blocos: int
    tokens_entrada: int
    tokens_saida: int


class _Contador:
    def __init__(self) -> None:
        self.entrada = 0
        self.saida = 0
        self.ultimo: LLMResult | None = None

    def registrar(self, resultado: LLMResult) -> str:
        self.entrada += resultado.tokens_entrada or 0
        self.saida += resultado.tokens_saida or 0
        self.ultimo = resultado
        return resultado.texto


def analisar(agente: Agente, texto_autos: str, esclarecimentos: str = "") -> ResultadoAnalise:
    """Envia os autos e o prompt do agente ao modelo vinculado.

    Se o texto exceder o orçamento de contexto do modelo, aplica map-reduce: cada
    bloco recebe uma análise parcial, e as parciais são consolidadas ao final.
    """
    contador = _Contador()
    modelo = agente.modelo
    orcamento = blocos.orcamento_entrada(modelo, agente.prompt + prompts.ANALISE_PARCIAL)
    conteudo = prompts.CABECALHO_AUTOS + texto_autos + esclarecimentos

    if blocos.cabe_no_contexto(conteudo, orcamento):
        texto = contador.registrar(
            ia.gerar(modelo, agente.prompt, conteudo, tarefa=Tarefa.ANALISE, agente=agente.slug)
        )
        quantidade_blocos = 1
    else:
        partes = blocos.dividir(texto_autos, orcamento - blocos.estimar_tokens(esclarecimentos))
        quantidade_blocos = len(partes)
        parciais = [
            contador.registrar(
                ia.gerar(
                    modelo,
                    agente.prompt + prompts.ANALISE_PARCIAL.format(indice=i, total=len(partes)),
                    prompts.CABECALHO_AUTOS + parte + esclarecimentos,
                    tarefa=Tarefa.PARCIAL,
                    agente=agente.slug,
                )
            )
            for i, parte in enumerate(partes, 1)
        ]
        texto = _consolidar(agente, parciais, orcamento, contador)

    assert contador.ultimo is not None
    return ResultadoAnalise(
        texto=texto.strip(),
        provedor=contador.ultimo.provedor,
        modelo=contador.ultimo.modelo,
        blocos=quantidade_blocos,
        tokens_entrada=contador.entrada,
        tokens_saida=contador.saida,
    )


def _juntar(parciais: list[str]) -> str:
    return "\n\n".join(
        f"=== ANÁLISE PARCIAL {i} de {len(parciais)} ===\n{texto}"
        for i, texto in enumerate(parciais, 1)
    )


def _consolidar(agente: Agente, parciais: list[str], orcamento: int, contador: _Contador) -> str:
    """Reduce hierárquico: consolida em grupos até restar uma única análise."""
    system_prompt = agente.prompt + prompts.CONSOLIDACAO
    for _ in range(MAXIMO_NIVEIS_CONSOLIDACAO):
        grupos = _agrupar(parciais, orcamento)
        parciais = [
            contador.registrar(
                ia.gerar(
                    agente.modelo,
                    system_prompt,
                    _juntar(grupo),
                    tarefa=Tarefa.CONSOLIDACAO,
                    agente=agente.slug,
                )
            )
            for grupo in grupos
        ]
        if len(parciais) == 1:
            return parciais[0]
    return "\n\n".join(parciais)


def _agrupar(parciais: list[str], orcamento: int) -> list[list[str]]:
    grupos: list[list[str]] = [[]]
    for parcial in parciais:
        candidato = [*grupos[-1], parcial]
        if grupos[-1] and not blocos.cabe_no_contexto(_juntar(candidato), orcamento):
            grupos.append([parcial])
        else:
            grupos[-1] = candidato
    return grupos
