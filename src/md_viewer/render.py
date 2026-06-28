"""Markdown -> HTML rendering pipeline."""
from __future__ import annotations

import re as _re

from markdown_it import MarkdownIt
from mdit_py_plugins.anchors import anchors_plugin
from mdit_py_plugins.attrs import attrs_plugin
from mdit_py_plugins.deflist import deflist_plugin
from mdit_py_plugins.front_matter import front_matter_plugin
from mdit_py_plugins.tasklists import tasklists_plugin
from nh3 import clean as nh3_clean

_md = MarkdownIt("gfm-like", {"html": True, "linkify": True, "typographer": True})
_md.enable(["replacements", "smartquotes"])
_md.use(anchors_plugin, max_level=3, min_level=1, permalink=False)
_md.use(attrs_plugin)
_md.use(deflist_plugin)
_md.use(front_matter_plugin)
_md.use(tasklists_plugin, enabled=True)


# === Sanitization whitelist (nh3) ===
ALLOWED_TAGS = {
    "a", "abbr", "b", "blockquote", "br", "code", "del", "div", "details",
    "summary", "em", "h1", "h2", "h3", "h4", "h5", "h6", "hr", "i", "img",
    "input", "ins", "kbd", "label", "li", "mark", "ol", "p", "pre", "s",
    "samp", "span", "strong", "sub", "sup", "svg", "table", "tbody", "td",
    "th", "thead", "tr", "u", "ul",
    # math / mermaid client hooks
    "math", "semantics", "mrow", "mi", "mo", "mn", "msup", "msub", "mfrac",
    "mtext", "annotation", "foreignObject",
}
ALLOWED_ATTRS = {
    "a": {"href", "title", "target", "class", "id"},  # rel managed by link_rel
    "img": {"src", "alt", "title", "class", "id", "width", "height"},
    "code": {"class", "id"},
    "pre": {"class", "id"},
    "span": {"class", "id", "style"},
    "div": {"class", "id"},
    "th": {"align", "scope"},
    "td": {"align"},
    "math": {"xmlns", "display"},
    "annotation": {"encoding"},
    "foreignObject": {"width", "height"},
    "svg": {"xmlns", "viewBox", "width", "height", "class"},
    "input": {"type", "checked", "disabled", "class"},
    "label": {"for", "class"},
    "ul": {"class"},
    "li": {"class"},
    "*": {"id", "class"},
}


def _escape_html(s: str) -> str:
    return (
        s.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _highlight(escaped: str, lang: str) -> str:
    try:
        from pygments import highlight as _hl
        from pygments.lexers import get_lexer_by_name
        from pygments.formatters import HtmlFormatter

        lexer = get_lexer_by_name(lang, stripall=True)
        formatter = HtmlFormatter(nowrap=False, cssclass="highlight")
        return _hl(escaped, lexer, formatter)
    except Exception:
        return escaped


def _render_fence(self, tokens, idx, options, env):
    token = tokens[idx]
    info = (token.info or "").strip()
    parts = info.split()
    lang = parts[0] if parts else ""
    content = token.content

    # Mermaid: emit a placeholder <pre class="mermaid"> for client hydration
    if lang == "mermaid":
        return f'<pre class="mermaid">{_escape_html(content)}</pre>\n'

    escaped = _escape_html(content)
    copyable = "copyable-code"
    cls = f"language-{lang}" if lang else ""
    body = _highlight(escaped, lang) if lang else escaped
    return f'<pre class="{copyable}"><code class="{cls}">{body}</code></pre>\n'


def _render_code_block(self, tokens, idx, options, env):
    token = tokens[idx]
    escaped = _escape_html(token.content)
    return f'<pre class="copyable-code"><code>{escaped}</code></pre>\n'


# Install custom fence/code_block renderers (must be after _md is defined)
_md.add_render_rule("fence", _render_fence)
_md.add_render_rule("code_block", _render_code_block)


# === Link post-processor (add rel/target to external links) ===
_LINK_RE = _re.compile(r'<a\s+([^>]*?)href="([^"]+)"([^>]*)>', _re.IGNORECASE)


def _post_process_links(html: str) -> str:
    def fix(match: _re.Match) -> str:
        before, href, after = match.group(1), match.group(2), match.group(3)
        is_external = href.startswith(("http://", "https://", "//"))
        target = ' target="_blank"' if is_external else ""
        return f'<a {before}href="{href}"{after}{target}>'
    return _LINK_RE.sub(fix, html)


_WIKILINK_RE = _re.compile(r"\[\[([^\]|]+)(?:\|([^\]]+))?\]\]")


def _wikilink_replace(match: _re.Match) -> str:
    target = match.group(1).strip()
    alias = (match.group(2) or "").strip() or target
    if target.lower().endswith((".md", ".markdown", ".mdx")):
        api_path = "/" + target.lstrip("/")
    else:
        api_path = "/" + target + ".md"
    return f"[{alias}](/api/file?path={api_path}){{class=wikilink}}"


def _preprocess_wikilinks(text: str) -> str:
    return _WIKILINK_RE.sub(_wikilink_replace, text)


def render_markdown(text: str) -> dict:
    """Render markdown to HTML and extract TOC + title.

    Returns dict with keys: html (str), toc (list[dict]), title (str|None).
    """
    text = _preprocess_wikilinks(text)
    tokens = _md.parse(text)
    html = _md.render(text)
    html = _post_process_links(html)
    html = nh3_clean(
        html,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRS,
        link_rel="noopener noreferrer",
    )

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
