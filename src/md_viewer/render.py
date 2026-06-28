"""Markdown -> HTML rendering pipeline."""
from __future__ import annotations

from markdown_it import MarkdownIt
from mdit_py_plugins.anchors import anchors_plugin
from mdit_py_plugins.attrs import attrs_plugin
from mdit_py_plugins.deflist import deflist_plugin
from mdit_py_plugins.front_matter import front_matter_plugin

_md = MarkdownIt("commonmark", {"html": True, "linkify": True, "typographer": True})
_md.enable(["replacements", "smartquotes"])
_md.enable("table")
_md.enable("strikethrough")
_md.use(anchors_plugin, max_level=3, min_level=1, permalink=False)
_md.use(attrs_plugin)
_md.use(deflist_plugin)
_md.use(front_matter_plugin)


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
    current_text: str = ""

    for tok in tokens:
        if tok.type == "heading_open":
            in_heading = True
            current_level = int(tok.tag[1])
            current_id = tok.attrGet("id")
            current_text = ""
        elif tok.type == "heading_close":
            if current_level <= 3:
                heading_text = current_text.strip()
                toc.append(
                    {"level": current_level, "text": heading_text, "id": current_id}
                )
                if current_level == 1 and title is None:
                    title = heading_text
            in_heading = False
        elif in_heading and tok.type == "inline":
            # inline.content is the flattened text of the heading
            current_text = tok.content

    return {"html": html, "toc": toc, "title": title}
