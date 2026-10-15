"""Alimentação da tabela consolidada de execuções a partir dos PDFs dos autos.

Para cada PDF: extração do texto → verificação de escopo → agente interno de
extração estruturada (JSON validado) → criação ou atualização da linha pelo número
do processo. Campos revisados pelo procurador prevalecem sobre a nova extração.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from typing import Any, BinaryIO

from django.db import transaction
from django.http import HttpRequest

from apps.agentes.models import Agente
from apps.analises.services import blocos, escopo, extracao
from apps.analises.services.qualidade import QualidadeExtracao
from apps.auditoria.services import Acao, Resultado, registrar
from apps.core.json_ia import JSONInvalidoError, ler_objeto_json
from apps.empresas import prompts
from apps.empresas.models import Empresa, ExecucaoFiscal, Situacao
from apps.provedores import services as ia
from apps.provedores.llm import LLMError, Tarefa

logger = logging.getLogger(__name__)

SLUG_AGENTE_EXTRACAO = "extracao-estruturada"
LIMITE_ITEM = 300
LIMITE_ITENS = 30


class ConsolidacaoError(Exception):
    """Falha ao processar o PDF (mensagem segura para o usuário)."""


class ForaDoEscopoError(ConsolidacaoError):
    """O documento não é um processo de execução fiscal."""


@dataclass(frozen=True)
class DadosExecucao:
    numero_processo: str
    cdas: list[str] = field(default_factory=list)
    valor_executado: Decimal | None = None
    bens_penhorados: list[str] = field(default_factory=list)
    apropriacoes: list[dict[str, str]] = field(default_factory=list)
    teses_defesa: list[str] = field(default_factory=list)
    situacao: str = Situacao.EM_ANDAMENTO
    situacao_detalhe: str = ""
    acao_imediata: bool = False


@dataclass(frozen=True)
class ResultadoProcessamento:
    execucao: ExecucaoFiscal
    criada: bool
    campos_preservados: list[str]
    qualidade: QualidadeExtracao


# --- validação do JSON devolvido pelo modelo -----------------------------------


def _lista_textos(valor: Any) -> list[str]:
    if isinstance(valor, str):
        valor = [valor] if valor.strip() else []
    if not isinstance(valor, list):
        return []
    itens = [str(v).strip()[:LIMITE_ITEM] for v in valor if v is not None and str(v).strip()]
    return list(dict.fromkeys(itens))[:LIMITE_ITENS]


def _decimal(valor: Any) -> Decimal | None:
    if valor in (None, "", []):
        return None
    texto = str(valor).replace("R$", "").strip()
    if "," in texto:  # formato brasileiro: 1.234,56
        texto = texto.replace(".", "").replace(",", ".")
    try:
        numero = Decimal(texto).quantize(Decimal("0.01"))
    except (InvalidOperation, ValueError):
        return None
    return numero if Decimal(0) <= numero < Decimal("1e13") else None


def _apropriacoes(valor: Any) -> list[dict[str, str]]:
    if not isinstance(valor, list):
        return []
    itens = []
    for item in valor[:LIMITE_ITENS]:
        if isinstance(item, dict):
            descricao = str(item.get("descricao", "")).strip()[:LIMITE_ITEM]
            protocolo = str(item.get("protocolo_sefa", "") or "").strip()[:60]
        else:
            descricao, protocolo = str(item).strip()[:LIMITE_ITEM], ""
        if descricao or protocolo:
            itens.append({"descricao": descricao, "protocolo_sefa": protocolo})
    return itens


def validar_dados(dados: dict[str, Any], numero_reserva: str = "") -> DadosExecucao:
    """Converte o JSON do modelo em dados tipados, descartando o que for inválido."""
    numero = str(dados.get("numero_processo") or "").strip()
    if not extracao.RE_NUMERO_PROCESSO.fullmatch(numero):
        numero = numero_reserva
    if not numero:
        raise ConsolidacaoError("Não foi possível identificar o número do processo no documento.")
    situacao = str(dados.get("situacao") or "")
    acao = dados.get("acao_imediata")
    return DadosExecucao(
        numero_processo=numero,
        cdas=_lista_textos(dados.get("cdas")),
        valor_executado=_decimal(dados.get("valor_executado")),
        bens_penhorados=_lista_textos(dados.get("bens_penhorados")),
        apropriacoes=_apropriacoes(dados.get("apropriacoes")),
        teses_defesa=_lista_textos(dados.get("teses_defesa")),
        situacao=situacao if situacao in Situacao.values else Situacao.EM_ANDAMENTO,
        situacao_detalhe=re.sub(r"\s+", " ", str(dados.get("situacao_detalhe") or ""))[:300],
        acao_imediata=acao is True or str(acao).lower() in {"true", "sim", "1"},
    )


# --- extração e upsert -------------------------------------------------------------


def agente_extracao() -> Agente:
    agente = Agente.objects.filter(slug=SLUG_AGENTE_EXTRACAO, ativo=True).first()
    if agente is None:
        raise ConsolidacaoError(
            "O agente interno de extração não está cadastrado ou ativo "
            "(execute python manage.py seed_agentes)."
        )
    return agente


def _extrair_bloco(agente: Agente, system_prompt: str, texto: str) -> dict[str, Any]:
    resposta = ia.gerar(
        agente.modelo,
        system_prompt,
        texto,
        json=True,
        tarefa=Tarefa.EXTRACAO,
        agente=agente.slug,
    )
    return ler_objeto_json(resposta.texto)


def extrair_dados(agente: Agente, texto: str) -> DadosExecucao:
    """Extrai os dados da execução; autos que excedem o contexto do modelo são
    processados em blocos, e os resultados parciais são combinados."""
    numero_reserva = extracao.detectar_numero_processo(texto)
    orcamento = blocos.orcamento_entrada(agente.modelo, agente.prompt + prompts.EXTRACAO_PARCIAL)
    partes = blocos.dividir(texto, orcamento)

    if len(partes) <= 1:
        try:
            dados = _extrair_bloco(agente, agente.prompt, texto)
        except JSONInvalidoError as erro:
            raise ConsolidacaoError("A extração estruturada não retornou um JSON válido.") from erro
        return validar_dados(dados, numero_reserva)

    parciais = []
    for indice, parte in enumerate(partes, 1):
        instrucao = prompts.EXTRACAO_PARCIAL.format(indice=indice, total=len(partes))
        try:
            dados = _extrair_bloco(agente, agente.prompt + instrucao, parte)
        except JSONInvalidoError:
            logger.warning("Bloco %d de %d sem JSON válido; ignorado.", indice, len(partes))
            continue
        parciais.append(validar_dados(dados, numero_reserva))
    if not parciais:
        raise ConsolidacaoError("A extração estruturada não retornou um JSON válido.")
    return mesclar(parciais)


def _unir(listas: list[list[Any]]) -> list[Any]:
    vistos: list[Any] = []
    for lista in listas:
        vistos += [item for item in lista if item not in vistos]
    return vistos[:LIMITE_ITENS]


def mesclar(parciais: list[DadosExecucao]) -> DadosExecucao:
    """Combina extrações de blocos consecutivos dos mesmos autos.

    Listas são unidas sem repetição; número do processo e valor executado vêm do
    primeiro bloco que os informar (petição inicial); a situação processual vem do
    bloco mais recente que a descrever.
    """
    recentes = [p for p in parciais if p.situacao_detalhe] or parciais
    ultimo = recentes[-1]
    return DadosExecucao(
        numero_processo=parciais[0].numero_processo,
        cdas=_unir([p.cdas for p in parciais]),
        valor_executado=next(
            (p.valor_executado for p in parciais if p.valor_executado is not None), None
        ),
        bens_penhorados=_unir([p.bens_penhorados for p in parciais]),
        apropriacoes=_unir([p.apropriacoes for p in parciais]),
        teses_defesa=_unir([p.teses_defesa for p in parciais]),
        situacao=ultimo.situacao,
        situacao_detalhe=ultimo.situacao_detalhe,
        acao_imediata=ultimo.acao_imediata,
    )


@transaction.atomic
def upsert(empresa: Empresa, dados: DadosExecucao) -> tuple[ExecucaoFiscal, bool, list[str]]:
    """Cria ou atualiza a linha pelo número do processo, preservando revisões humanas."""
    execucao = (
        ExecucaoFiscal.objects.select_for_update()
        .filter(numero_processo=dados.numero_processo)
        .first()
    )
    criada = execucao is None
    if criada:
        execucao = ExecucaoFiscal(empresa=empresa, numero_processo=dados.numero_processo)
    elif execucao.empresa_id != empresa.pk:
        raise ConsolidacaoError(
            f"O processo {dados.numero_processo} já está vinculado a outra empresa "
            f"({execucao.empresa})."
        )

    preservados = []
    for campo in ExecucaoFiscal.CAMPOS_EXTRAIDOS:
        if campo == "numero_processo":
            continue
        if execucao.foi_revisado(campo):
            preservados.append(campo)
            continue
        setattr(execucao, campo, getattr(dados, campo))
    execucao.save()
    return execucao, criada, preservados


def processar_pdf(
    request: HttpRequest, empresa: Empresa, arquivo: BinaryIO
) -> ResultadoProcessamento:
    """Fluxo completo para um PDF; o texto extraído é descartado ao final."""
    agente = agente_extracao()
    base_log = {
        "request": request,
        "agente": agente.nome,
        "provedor": agente.modelo.provedor.tipo,
        "modelo": agente.modelo.identificador,
        "objeto": f"Empresa #{empresa.pk}",
    }
    numero = ""
    try:
        extraido = extracao.extrair_texto(arquivo)
        numero = extraido.numero_processo
        verificacao = escopo.verificar(extraido.texto, agente.modelo)
        if not verificacao.aceito:
            registrar(Acao.RECUSA_ESCOPO, numero_processo=numero, resultado=Resultado.RECUSADO,
                      detalhe="Tabela consolidada", **base_log)  # fmt: skip
            raise ForaDoEscopoError(escopo.MENSAGEM_RECUSA)
        dados = extrair_dados(agente, extraido.texto)
        numero = dados.numero_processo
        execucao, criada, preservados = upsert(empresa, dados)
    except (extracao.PDFInvalidoError, LLMError) as erro:
        registrar(Acao.EXTRACAO_EXECUCAO, numero_processo=numero, resultado=Resultado.ERRO,
                  detalhe=type(erro).__name__, **base_log)  # fmt: skip
        raise ConsolidacaoError(str(erro)) from erro
    except ForaDoEscopoError:
        raise
    except ConsolidacaoError:
        registrar(Acao.EXTRACAO_EXECUCAO, numero_processo=numero, resultado=Resultado.ERRO,
                  detalhe="Dados não consolidados", **base_log)  # fmt: skip
        raise

    registrar(
        Acao.EXTRACAO_EXECUCAO,
        numero_processo=numero,
        detalhe=(
            f"{'criada' if criada else 'atualizada'}; qualidade={extraido.qualidade.percentual}%; "
            f"campos preservados={len(preservados)}"
        ),
        **base_log,
    )
    return ResultadoProcessamento(execucao, criada, preservados, extraido.qualidade)
