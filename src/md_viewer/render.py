"""Markdown -> HTML rendering pipeline."""
from __future__ import annotations

from markdown_it import MarkdownIt

_md = MarkdownIt("commonmark", {"html": True, "linkify": True, "typographer": True})
_md.enable(["replacements", "smartquotes"])


def render_markdown(text: str) -> dict:
    """Render markdown to HTML and extract TOC + title.

    Returns dict with keys: html (str), toc (list[dict]), title (str|None).
    """
    tokens = _md.parse(text)
    html = _md.render(text)

    toc: list[dict] = []
    title: str | None = None
    in_heading = False
    current_level = 0
    current_id: str | None = None
    current_text: list[str] = []

    for tok in tokens:
        if tok.type == "heading_open":
            in_heading = True
            current_level = int(tok.tag[1])
            current_id = tok.attrGet("id")
            current_text = []
        elif tok.type == "heading_close":
            if current_level <= 3:
                heading_text = "".join(current_text).strip()
                toc.append(
                    {"level": current_level, "text": heading_text, "id": current_id}
                )
                if current_level == 1 and title is None:
                    title = heading_text
            in_heading = False
        elif in_heading and tok.type == "inline":
            current_text.append(tok.content)
            for child in tok.children or []:
                if child.type == "text":
                    current_text.append(child.content)

    return {"html": html, "toc": toc, "title": title}
