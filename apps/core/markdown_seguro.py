"""Conversão do Markdown gerado pelos modelos em HTML sanitizado."""

from __future__ import annotations

import markdown
import nh3

TAGS_PERMITIDAS = {
    "p", "br", "hr", "strong", "em", "b", "i", "u", "code", "pre", "blockquote",
    "h1", "h2", "h3", "h4", "h5", "h6", "ul", "ol", "li",
    "table", "thead", "tbody", "tr", "th", "td",
}  # fmt: skip


def para_html(texto: str) -> str:
    """Renderiza Markdown e remove qualquer HTML, script ou link não permitido."""
    html = markdown.markdown(texto, extensions=["tables", "sane_lists"])
    html = nh3.clean(html, tags=TAGS_PERMITIDAS, attributes={}, url_schemes=set())
    return html.replace("<table>", '<table class="table table-sm table-bordered">')
