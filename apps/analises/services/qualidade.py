"""Índice de qualidade da extração de texto do PDF.

Combina três medidas, cada uma normalizada entre 0 e 1:

- densidade: média de caracteres por página (documentos digitados têm ~1.500+;
  páginas digitalizadas sem OCR ficam próximas de zero);
- proporção de caracteres válidos (letras, números, pontuação usual) — texto
  corrompido ou extraído de manuscritos tende a gerar símbolos espúrios;
- proporção de páginas com texto.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

CARACTERES_REFERENCIA = 800
MINIMO_PAGINA_COM_TEXTO = 40
_VALIDOS = re.compile(r"[\wÀ-ÿ\s.,;:!?()\[\]{}\-–—/\\'\"ºª°§$%&@*+=<>|#_…]")

PESOS = {"densidade": 0.4, "validos": 0.4, "paginas": 0.2}


@dataclass(frozen=True)
class QualidadeExtracao:
    indice: float
    paginas: int
    paginas_sem_texto: int
    caracteres_por_pagina: float
    proporcao_validos: float
    limiar: float
    motivos: list[str] = field(default_factory=list)

    @property
    def baixa(self) -> bool:
        return self.indice < self.limiar

    @property
    def percentual(self) -> int:
        return round(self.indice * 100)

    def como_dict(self) -> dict:
        return {
            "indice": self.indice,
            "paginas": self.paginas,
            "paginas_sem_texto": self.paginas_sem_texto,
            "caracteres_por_pagina": self.caracteres_por_pagina,
            "proporcao_validos": self.proporcao_validos,
            "limiar": self.limiar,
            "motivos": self.motivos,
        }

    @classmethod
    def de_dict(cls, dados: dict) -> QualidadeExtracao:
        return cls(**dados)


def avaliar(paginas: list[str], limiar: float) -> QualidadeExtracao:
    total_paginas = len(paginas)
    if total_paginas == 0:
        return QualidadeExtracao(0.0, 0, 0, 0.0, 0.0, limiar, ["O PDF não possui páginas."])

    texto = "".join(paginas)
    sem_espacos = re.sub(r"\s", "", texto)
    sem_texto = sum(1 for p in paginas if len(p.strip()) < MINIMO_PAGINA_COM_TEXTO)
    por_pagina = len(sem_espacos) / total_paginas
    validos = len(_VALIDOS.findall(texto)) / len(texto) if texto else 0.0

    densidade = min(1.0, por_pagina / CARACTERES_REFERENCIA)
    com_texto = 1 - sem_texto / total_paginas
    indice = (
        PESOS["densidade"] * densidade + PESOS["validos"] * validos + PESOS["paginas"] * com_texto
    )

    motivos = []
    if densidade < 0.5:
        motivos.append(
            f"Pouco texto por página (média de {por_pagina:.0f} caracteres): o documento pode "
            "estar digitalizado sem OCR."
        )
    if texto and validos < 0.9:
        motivos.append(
            f"Apenas {validos:.0%} dos caracteres são reconhecíveis: o texto pode estar "
            "corrompido ou conter trechos manuscritos."
        )
    if sem_texto:
        motivos.append(f"{sem_texto} de {total_paginas} página(s) sem texto extraível.")

    return QualidadeExtracao(
        indice=round(indice, 3),
        paginas=total_paginas,
        paginas_sem_texto=sem_texto,
        caracteres_por_pagina=round(por_pagina, 1),
        proporcao_validos=round(validos, 3),
        limiar=limiar,
        motivos=motivos,
    )
