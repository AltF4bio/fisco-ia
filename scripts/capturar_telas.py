"""Percorre o fluxo completo em modo demonstração e salva capturas de tela.

Serve a dois propósitos: gerar as imagens de docs/screenshots/ usadas no README e
validar, de ponta a ponta, o sistema em execução (falha se algo não funcionar).

Pré-requisitos:
    pip install -r requirements-docs.txt && python -m playwright install chromium
    docker compose up -d            # ou runserver com seed_demo executado
    python scripts/gerar_pdfs_ficticios.py

Uso:
    python scripts/capturar_telas.py [url_base]      # padrão: http://localhost:8000
"""

from __future__ import annotations

import re
import sys
import tempfile
from pathlib import Path

from playwright.sync_api import Page, expect, sync_playwright

RAIZ = Path(__file__).resolve().parent.parent
EXEMPLOS = RAIZ / "exemplos"
SAIDA = RAIZ / "docs" / "screenshots"
SENHA = "Fisco.Demo-2026"


def capturar(page: Page, nome: str, pagina_inteira: bool = False) -> None:
    page.wait_for_load_state("networkidle")
    page.screenshot(path=SAIDA / f"{nome}.png", full_page=pagina_inteira)
    sys.stdout.write(f"  ✓ {nome}.png\n")


def entrar(page: Page, base: str, usuario: str) -> None:
    page.goto(f"{base}/contas/entrar/")
    page.fill("#id_username", usuario)
    page.fill("#id_password", SENHA)
    page.click("button[type=submit]")
    expect(page.get_by_text("Suas últimas atividades")).to_be_visible()


def sair(page: Page) -> None:
    page.click("text=Sair")
    expect(page.get_by_text("Acesso restrito")).to_be_visible()


def analisar(page: Page, base: str, pdf: str, agente: str) -> None:
    page.goto(f"{base}/analises/nova/")
    page.set_input_files("#id_arquivo", str(EXEMPLOS / pdf))
    page.select_option("#id_agente", label=agente)
    page.click("#botao-analisar")
    page.wait_for_load_state("networkidle")


def main(base: str) -> None:
    SAIDA.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        navegador = p.chromium.launch(channel="chromium", args=["--lang=pt-BR"])
        page = navegador.new_page(viewport={"width": 1440, "height": 900}, locale="pt-BR")

        sys.stdout.write("Procurador\n")
        page.goto(f"{base}/contas/entrar/")
        capturar(page, "01-login")
        entrar(page, base, "procurador.demo")
        capturar(page, "02-painel-procurador")

        # Análise com modo interativo de esclarecimento.
        page.goto(f"{base}/analises/nova/")
        capturar(page, "03-nova-analise")
        analisar(page, base, "execucao_fiscal_01_modo_interativo.pdf", "Resumo cronológico")
        expect(page).to_have_url(re.compile(r"/analises/esclarecimentos/$"))
        page.fill("#id_p1", "As benfeitorias consistem em galpão industrial de 1.200 m² (fl. 41).")
        capturar(page, "04-perguntas-esclarecimento", pagina_inteira=True)
        page.click("#botao-concluir")
        expect(page.get_by_text("Esclarecimentos do procurador considerados")).to_be_visible()
        capturar(page, "05-resultado-analise", pagina_inteira=True)

        with page.expect_download() as download:
            page.click("text=Exportar PDF")
        destino = Path(tempfile.gettempdir()) / "fisco-ia-analise.pdf"
        download.value.save_as(destino)
        assert destino.read_bytes().startswith(b"%PDF"), "Exportação em PDF falhou"
        sys.stdout.write("  ✓ análise exportada em PDF\n")

        # Map-reduce, alerta de qualidade e recusa por escopo.
        analisar(
            page,
            base,
            "execucao_fiscal_02_extensa_map_reduce.pdf",
            "Diagnóstico da situação processual",
        )
        expect(page.get_by_text(re.compile(r"Map-reduce em \d+ blocos"))).to_be_visible()
        sys.stdout.write("  ✓ map-reduce acionado\n")
        analisar(page, base, "execucao_fiscal_03_digitalizada_sem_ocr.pdf", "Síntese de decisões")
        expect(page.get_by_text("Baixa qualidade de extração")).to_be_visible()
        capturar(page, "06-alerta-qualidade")
        analisar(page, base, "documento_fora_do_escopo.pdf", "Síntese de decisões")
        expect(page.get_by_text("Documento fora do escopo")).to_be_visible()
        capturar(page, "07-recusa-escopo")

        # Empresa e tabela consolidada.
        page.goto(f"{base}/empresas/")
        page.click("text=Metalúrgica Horizonte Fictícia Ltda.")
        page.set_input_files(
            "input[name=arquivos]",
            [
                str(EXEMPLOS / "execucao_fiscal_01_modo_interativo.pdf"),
                str(EXEMPLOS / "execucao_fiscal_02_extensa_map_reduce.pdf"),
            ],
        )
        page.click("#botao-envio")
        expect(page.get_by_text("0004567-89.2019.8.16.0014").first).to_be_visible()
        page.locator("a[title='Revisar dados']").first.click()
        page.fill("#id_situacao_detalhe", "Prazo para contrarrazões à apelação em curso (Mov. 15).")
        page.click("text=Salvar revisão")
        expect(page.get_by_text("Revisão salva")).to_be_visible()
        capturar(page, "08-empresa-tabela-consolidada", pagina_inteira=True)
        with page.expect_download() as csv:
            page.click("text=Exportar CSV")
        assert csv.value.suggested_filename.endswith(".csv")
        with page.expect_download() as pdf:
            page.click("text=Exportar PDF")
        assert pdf.value.suggested_filename.endswith(".pdf")
        sys.stdout.write("  ✓ tabela exportada em CSV e PDF\n")
        sair(page)

        sys.stdout.write("Administrador\n")
        entrar(page, base, "admin.demo")
        capturar(page, "09-painel-administrador")
        page.goto(f"{base}/provedores/")
        capturar(page, "10-provedores", pagina_inteira=True)
        cartao_demo = page.locator(".card", has_text="Demonstração (MockProvider)")
        cartao_demo.get_by_role("button", name="Testar conexão").click()
        expect(page.get_by_text("Provedor de demonstração ativo").first).to_be_visible()
        page.goto(f"{base}/agentes/")
        capturar(page, "11-agentes")
        page.click("text=Editar >> nth=0")
        capturar(page, "12-agente-edicao")
        page.goto(f"{base}/contas/usuarios/")
        capturar(page, "13-usuarios")
        page.goto(f"{base}/auditoria/")
        expect(page.locator("td", has_text="Recusa por escopo").first).to_be_visible()
        capturar(page, "14-auditoria")

        # O procurador não acessa telas administrativas.
        sair(page)
        entrar(page, base, "procurador.demo")
        resposta = page.goto(f"{base}/provedores/")
        assert resposta is not None and resposta.status == 403, "Procurador acessou provedores"
        sys.stdout.write("  ✓ procurador bloqueado nas telas administrativas (403)\n")

        navegador.close()
    sys.stdout.write("Fluxo completo validado.\n")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000")
