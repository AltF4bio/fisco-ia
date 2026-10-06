"""Modo interativo de esclarecimento: perguntas estruturadas ao procurador."""

from __future__ import annotations

from dataclasses import asdict, dataclass

from apps.agentes.models import Agente
from apps.analises import prompts
from apps.analises.services import blocos
from apps.core.json_ia import JSONInvalidoError, ler_objeto_json
from apps.provedores import services as ia
from apps.provedores.llm import Tarefa

MAXIMO_PERGUNTAS = 5
LIMITE_PERGUNTA = 500
LIMITE_RESPOSTA = 2_000


@dataclass(frozen=True)
class Pergunta:
    id: str
    pergunta: str
    referencia: str = ""

    def como_dict(self) -> dict:
        return asdict(self)


def _validar(dados: dict) -> list[Pergunta]:
    """Aceita apenas o formato esperado; itens malformados são descartados."""
    itens = dados.get("perguntas")
    if not isinstance(itens, list):
        raise JSONInvalidoError("Campo 'perguntas' ausente ou inválido.")
    perguntas = []
    for item in itens:
        if not isinstance(item, dict) or not str(item.get("pergunta", "")).strip():
            continue
        perguntas.append(
            Pergunta(
                id=f"p{len(perguntas) + 1}",
                pergunta=str(item["pergunta"]).strip()[:LIMITE_PERGUNTA],
                referencia=str(item.get("referencia", "")).strip()[:60],
            )
        )
    return perguntas


def gerar_perguntas(agente: Agente, texto: str) -> list[Pergunta]:
    """Pede ao modelo as lacunas dos autos. Lista vazia = seguir direto para a análise."""
    system_prompt = prompts.ESCLARECIMENTO + agente.prompt
    orcamento = blocos.orcamento_entrada(agente.modelo, system_prompt)
    perguntas: list[Pergunta] = []
    for bloco in blocos.dividir(texto, orcamento):
        resposta = ia.gerar(
            agente.modelo,
            system_prompt,
            prompts.CABECALHO_AUTOS + bloco,
            json=True,
            max_tokens=2_000,
            tarefa=Tarefa.PERGUNTAS,
            agente=agente.slug,
        )
        try:
            perguntas += _validar(ler_objeto_json(resposta.texto))
        except JSONInvalidoError:
            continue  # sem perguntas aproveitáveis neste bloco: segue para a análise
        if len(perguntas) >= MAXIMO_PERGUNTAS:
            break
    return [
        Pergunta(id=f"p{i}", pergunta=p.pergunta, referencia=p.referencia)
        for i, p in enumerate(perguntas[:MAXIMO_PERGUNTAS], 1)
    ]


def formatar_esclarecimentos(perguntas: list[Pergunta], respostas: dict[str, str]) -> str:
    """Texto incorporado à análise final com as respostas do procurador."""
    linhas = []
    for pergunta in perguntas:
        resposta = respostas.get(pergunta.id, "").strip()[:LIMITE_RESPOSTA]
        referencia = f" ({pergunta.referencia})" if pergunta.referencia else ""
        # Dois espaços ao fim da linha = quebra de linha no Markdown.
        linhas.append(f"- **Pergunta{referencia}:** {pergunta.pergunta}  ")
        linhas.append(
            f"  **Resposta do procurador:** {resposta or 'Sem resposta (informação indisponível).'}"
        )
    return prompts.CABECALHO_ESCLARECIMENTOS + "\n".join(linhas)
