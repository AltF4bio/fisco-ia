"""Exportação da análise em PDF."""

from __future__ import annotations

from datetime import datetime

from django.utils import timezone
from reportlab.platypus import Paragraph, Spacer

from apps.core import pdf


def _data_hora(valor: str | datetime) -> str:
    momento = datetime.fromisoformat(valor) if isinstance(valor, str) else valor
    return timezone.localtime(momento).strftime("%d/%m/%Y %H:%M")


def analise_em_pdf(resultado: dict, exportado_por: str) -> bytes:
    """PDF com cabeçalho, metadados, corpo da análise e aviso institucional."""
    estilos = pdf.estilos()
    metadados = [
        ("Número do processo", resultado.get("numero_processo") or "Não identificado"),
        ("Agente", resultado["agente"]),
        ("Modelo utilizado", f"{resultado['provedor']} / {resultado['modelo']}"),
        ("Data/hora da análise", _data_hora(resultado["criado_em"])),
        ("Usuário", resultado["usuario"]),
        ("Exportado por / em", f"{exportado_por} — {_data_hora(timezone.now())}"),
    ]
    if resultado.get("blocos", 1) > 1:
        metadados.append(("Processamento", f"Map-reduce em {resultado['blocos']} blocos"))
    if resultado.get("com_esclarecimentos"):
        metadados.append(("Esclarecimentos", "Incorporadas respostas do procurador"))

    elementos = [pdf.tabela_metadados(metadados, pdf.largura_util()), Spacer(1, 6)]
    qualidade = resultado.get("qualidade") or {}
    if qualidade and qualidade["indice"] < qualidade["limiar"]:
        elementos.append(
            Paragraph(
                "<b>Atenção — baixa qualidade de extração "
                f"({round(qualidade['indice'] * 100)}%).</b> "
                "O documento pode estar digitalizado sem OCR, manuscrito ou corrompido; "
                "a análise pode ser imprecisa.",
                estilos["aviso"],
            )
        )
        elementos.append(Spacer(1, 8))
    elementos.append(pdf.bloco_aviso_ia())
    elementos += pdf.markdown_para_flowables(resultado["texto"])
    elementos.append(pdf.bloco_aviso_ia())
    return pdf.gerar_pdf(f"Análise — {resultado['agente']}", elementos)
