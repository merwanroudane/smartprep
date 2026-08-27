"""Report generation.

Markdown and JSON first: both are diffable, reviewable and impossible to
silently truncate. HTML builds on the same EDA objects and chart specs, so the
three cannot drift apart.
"""

from .html import HtmlDocument, Section, preparation_html, scan_html, studio_html
from .markdown import comparison_report, preparation_report, scan_report
from .publish import Deck, Slide, build_deck, publish, to_notebook, to_pdf, to_pptx

__all__ = [
    "scan_report",
    "preparation_report",
    "comparison_report",
    "scan_html",
    "preparation_html",
    "studio_html",
    "HtmlDocument",
    "Section",
    "publish",
    "to_pdf",
    "to_pptx",
    "to_notebook",
    "build_deck",
    "Deck",
    "Slide",
]
