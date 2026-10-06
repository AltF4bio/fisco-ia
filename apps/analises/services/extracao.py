"""Extração do texto do PDF dos autos.

O arquivo é lido diretamente do upload (memória ou arquivo temporário do Django,
descartado ao fim da requisição). Nada é gravado no banco ou em MEDIA_ROOT.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import BinaryIO

import pdfplumber
import pypdf
from django.conf import settings

from apps.analises.services.qualidade import QualidadeExtracao, avaliar

logger = logging.getLogger(__name__)

RE_NUMERO_PROCESSO = re.compile(r"\b\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}\b")


class PDFInvalidoError(Exception):
    """O arquivo não pôde ser lido como PDF."""


@dataclass(frozen=True)
class TextoExtraido:
    texto: str
    qualidade: QualidadeExtracao

    @property
    def numero_processo(self) -> str:
        return detectar_numero_processo(self.texto)


def detectar_numero_processo(texto: str) -> str:
    """Primeiro número de processo no padrão CNJ encontrado no texto."""
    encontrado = RE_NUMERO_PROCESSO.search(texto)
    return encontrado.group(0) if encontrado else ""


def _paginas_pdfplumber(arquivo: BinaryIO) -> list[str]:
    with pdfplumber.open(arquivo) as pdf:
        return [pagina.extract_text() or "" for pagina in pdf.pages]


def _paginas_pypdf(arquivo: BinaryIO) -> list[str]:
    leitor = pypdf.PdfReader(arquivo)
    return [pagina.extract_text() or "" for pagina in leitor.pages]


def extrair_paginas(arquivo: BinaryIO) -> list[str]:
    """Texto de cada página, com pdfplumber e, em caso de falha, pypdf."""
    try:
        return _paginas_pdfplumber(arquivo)
    except Exception as erro:
        logger.info("pdfplumber falhou (%s); usando pypdf.", type(erro).__name__)
    try:
        arquivo.seek(0)
        return _paginas_pypdf(arquivo)
    except Exception as erro:
        raise PDFInvalidoError("Não foi possível ler o arquivo como PDF.") from erro


def extrair_texto(arquivo: BinaryIO, limiar: float | None = None) -> TextoExtraido:
    """Extrai o texto, marcando o início de cada folha para permitir citações."""
    paginas = extrair_paginas(arquivo)
    limiar = settings.FISCO_LIMIAR_QUALIDADE if limiar is None else limiar
    texto = "\n\n".join(
        f"--- [fl. {numero}] ---\n{conteudo.strip()}" for numero, conteudo in enumerate(paginas, 1)
    )
    return TextoExtraido(texto=texto, qualidade=avaliar(paginas, limiar))
