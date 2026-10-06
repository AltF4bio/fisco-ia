"""Orquestração do fluxo de análise de autos.

PDF → extração e índice de qualidade → verificação de escopo → (perguntas de
esclarecimento) → análise pelo agente (com map-reduce) → resultado na sessão.

O log de auditoria recebe apenas metadados: nunca trechos dos autos, perguntas,
respostas ou o texto da análise.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import BinaryIO, Literal

from django.http import HttpRequest

from apps.agentes.models import Agente
from apps.analises.services import escopo, executor, extracao, interativo, sessao
from apps.analises.services.qualidade import QualidadeExtracao
from apps.auditoria.services import Acao, Resultado, registrar
from apps.provedores.llm import LLMError

Etapa = Literal["concluido", "perguntas", "recusado", "erro"]


@dataclass
class ResultadoFluxo:
    etapa: Etapa
    mensagem: str = ""
    resultado_id: str = ""
    detalhes: list[str] = field(default_factory=list)


def _auditar(request: HttpRequest, acao: Acao, agente: Agente, numero: str, **extra) -> None:
    registrar(
        acao,
        request=request,
        numero_processo=numero,
        agente=agente.nome,
        provedor=extra.pop("provedor", agente.modelo.provedor.tipo),
        modelo=extra.pop("modelo", agente.modelo.identificador),
        **extra,
    )


def iniciar(
    request: HttpRequest, arquivo: BinaryIO, agente: Agente, numero_informado: str = ""
) -> ResultadoFluxo:
    sessao.limpar_temporarios_expirados()
    sessao.cancelar_pendente(request.session)

    try:
        extraido = extracao.extrair_texto(arquivo)
    except extracao.PDFInvalidoError as erro:
        _auditar(request, Acao.ANALISE, agente, numero_informado, resultado=Resultado.ERRO,
                 detalhe="PDF ilegível")  # fmt: skip
        return ResultadoFluxo("erro", str(erro))

    numero = numero_informado or extraido.numero_processo
    try:
        verificacao = escopo.verificar(extraido.texto, agente.modelo)
        if not verificacao.aceito:
            _auditar(
                request,
                Acao.RECUSA_ESCOPO,
                agente,
                numero,
                resultado=Resultado.RECUSADO,
                detalhe=f"Termos característicos encontrados: {len(verificacao.termos)}",
            )
            return ResultadoFluxo(
                "recusado", escopo.MENSAGEM_RECUSA, detalhes=[verificacao.justificativa]
            )

        if agente.modo_interativo:
            perguntas = interativo.gerar_perguntas(agente, extraido.texto)
            if perguntas:
                sessao.iniciar_pendente(
                    request.session,
                    extraido.texto,
                    {
                        "agente_id": agente.pk,
                        "numero_processo": numero,
                        "qualidade": extraido.qualidade.como_dict(),
                        "perguntas": [p.como_dict() for p in perguntas],
                    },
                )
                _auditar(request, Acao.ESCLARECIMENTO, agente, numero,
                         detalhe=f"{len(perguntas)} pergunta(s) ao procurador")  # fmt: skip
                return ResultadoFluxo("perguntas")

        return _concluir(request, agente, extraido.texto, numero, extraido.qualidade)
    except LLMError as erro:
        _auditar(request, Acao.ANALISE, agente, numero, resultado=Resultado.ERRO,
                 detalhe=type(erro).__name__)  # fmt: skip
        return ResultadoFluxo("erro", str(erro))


def responder(request: HttpRequest, respostas: dict[str, str]) -> ResultadoFluxo:
    pendente = sessao.obter_pendente(request.session)
    if pendente is None:
        return ResultadoFluxo("erro", "Não há análise aguardando esclarecimentos.")
    agente = Agente.objects.filter(pk=pendente["agente_id"], ativo=True).first()
    texto = sessao.ler_texto_temporario(pendente["token"])
    try:
        if agente is None or texto is None:
            return ResultadoFluxo(
                "erro",
                "A análise pendente expirou ou o agente foi desativado. Envie o PDF novamente.",
            )
        perguntas = [interativo.Pergunta(**p) for p in pendente["perguntas"]]
        esclarecimentos = interativo.formatar_esclarecimentos(perguntas, respostas)
        qualidade = QualidadeExtracao.de_dict(pendente["qualidade"])
        return _concluir(
            request, agente, texto, pendente["numero_processo"], qualidade, esclarecimentos
        )
    except LLMError as erro:
        _auditar(request, Acao.ANALISE, agente, pendente["numero_processo"],
                 resultado=Resultado.ERRO, detalhe=type(erro).__name__)  # fmt: skip
        return ResultadoFluxo("erro", str(erro))
    finally:
        # LGPD: o texto dos autos é descartado após a geração da análise.
        sessao.cancelar_pendente(request.session)


def _concluir(
    request: HttpRequest,
    agente: Agente,
    texto: str,
    numero: str,
    qualidade: QualidadeExtracao,
    esclarecimentos: str = "",
) -> ResultadoFluxo:
    analise = executor.analisar(agente, texto, esclarecimentos)
    identificador = sessao.guardar_resultado(
        request.session,
        {
            "agente": agente.nome,
            "agente_slug": agente.slug,
            "provedor": analise.provedor,
            "modelo": analise.modelo,
            "numero_processo": numero,
            "usuario": request.user.get_full_name() or request.user.get_username(),
            "texto": analise.texto,
            "blocos": analise.blocos,
            "com_esclarecimentos": bool(esclarecimentos),
            "qualidade": qualidade.como_dict(),
        },
    )
    _auditar(
        request,
        Acao.ANALISE,
        agente,
        numero,
        provedor=analise.provedor,
        modelo=analise.modelo,
        detalhe=(
            f"blocos={analise.blocos}; qualidade={qualidade.percentual}%; "
            f"tokens={analise.tokens_entrada}/{analise.tokens_saida}"
        ),
    )
    return ResultadoFluxo("concluido", resultado_id=identificador)
