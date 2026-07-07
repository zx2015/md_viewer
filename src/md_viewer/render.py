"""Markdown -> HTML rendering pipeline."""
from __future__ import annotations

import html as _html
import json as _json
import posixpath as _posixpath
import re as _re
from pathlib import Path as _Path
from urllib.parse import quote as _quote
from urllib.parse import unquote as _unquote
from urllib.parse import urlsplit as _urlsplit

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
    # IMPORTANT: ``escaped`` is intentionally the *raw* source text — Pygments
    # does its own HTML escaping internally via HtmlFormatter. Pre-escaping
    # would cause double-escape (e.g. ``"`` → ``&quot;`` → ``&amp;quot;``).
    try:
        from pygments import highlight as _hl
        from pygments.lexers import get_lexer_by_name
        from pygments.formatters import HtmlFormatter

        lexer = get_lexer_by_name(lang, stripall=True)
        formatter = HtmlFormatter(nowrap=False, cssclass="highlight")
        return _hl(escaped, lexer, formatter)
    except Exception:
        # Fallback: at minimum the source must be HTML-safe
        return _escape_html(escaped)


def _render_fence(self, tokens, idx, options, env):
    token = tokens[idx]
    info = (token.info or "").strip()
    parts = info.split()
    lang = parts[0] if parts else ""
    content = token.content

    # Mermaid: emit a placeholder <pre class="mermaid"> for client hydration
    if lang == "mermaid":
        return f'<pre class="mermaid">{_escape_html(content)}</pre>\n'

    # IMPORTANT: pass raw content to Pygments — it does its own HTML escaping
    # internally. Pre-escaping would cause double-escape of `"`, `&`, etc.
    copyable = "copyable-code"
    cls = f"language-{lang}" if lang else ""
    body = _highlight(content, lang) if lang else _escape_html(content)
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
_CONTENT_LINK_EXTS = (".md", ".markdown", ".mdx", ".py", ".json", ".html", ".htm")


def _resolve_local_href(href_path: str, current_file_path: str) -> str:
    base_dir = _posixpath.dirname(current_file_path) or "/"
    if href_path.startswith("/"):
        joined = href_path
    else:
        joined = _posixpath.join(base_dir, href_path)
    normalized = _posixpath.normpath("/" + joined.lstrip("/"))
    return normalized if normalized.startswith("/") else "/" + normalized


def _rewrite_local_file_href(href: str, current_file_path: str | None) -> str:
    if not current_file_path:
        return href
    if href.startswith("/api/file?path="):
        return href
    if href.startswith(("#", "?")):
        return href

    parsed = _urlsplit(href)
    if parsed.scheme or parsed.netloc:
        return href
    if parsed.query:
        return href

    decoded_path = _unquote(parsed.path or "")
    if not decoded_path:
        return href
    if not decoded_path.lower().endswith(_CONTENT_LINK_EXTS):
        return href

    resolved = _resolve_local_href(decoded_path, current_file_path)
    api_href = f'/api/file?path={_quote(resolved, safe="/")}'
    if parsed.fragment:
        return f"{api_href}#{parsed.fragment}"
    return api_href


def _post_process_links(html: str, current_file_path: str | None = None) -> str:
    def fix(match: _re.Match) -> str:
        before, href, after = match.group(1), match.group(2), match.group(3)
        href = _rewrite_local_file_href(href, current_file_path)
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


def render_markdown(text: str, current_file_path: str | None = None) -> dict:
    """Render markdown to HTML and extract TOC + title.

    Returns dict with keys: html (str), toc (list[dict]), title (str|None).
    """
    text = _preprocess_wikilinks(text)
    tokens = _md.parse(text)
    html = _md.render(text)
    html = _post_process_links(html, current_file_path=current_file_path)
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


# === render_viewable dispatcher (new in v2) ===

# Mapping from extension to Pygments lexer name.
_CODE_LANG_BY_EXT = {
    ".py": "python",
    ".json": "json",
    ".html": "html",
    ".htm": "html",
}


def _render_code_view(text: str, lang: str) -> str:
    """Render plain text as a syntax-highlighted <pre> block.

    Pygments handles its own HTML escaping, so we pass the raw text in.
    """
    cls = f"language-{lang}" if lang else ""
    body = _highlight(text, lang) if lang else _escape_html(text)
    return f'<pre class="copyable-code"><code class="{cls}">{body}</code></pre>\n'


def _render_html_preview(text: str) -> str:
    """Build a sandboxed <iframe srcdoc> wrapper around the given HTML source.

    The source is HTML-escaped so the attribute value is well-formed; the
    browser decodes it back to the original HTML for rendering inside the
    sandboxed iframe.
    """
    srcdoc = _html.escape(text, quote=True)
    return (
        f'<iframe class="html-preview" sandbox="" srcdoc="{srcdoc}" '
        f'referrerpolicy="no-referrer"></iframe>\n'
    )


def render_viewable(
    filename: str, text: str, current_file_path: str | None = None
) -> dict:
    """Render a file's text into the unified response dict used by /api/file.

    Returns a dict with these keys:
        {
          "kind": "markdown" | "code" | "code-error" | "html",
          "html": str,                 # primary HTML to inject into the main pane
          "toc": list[dict],           # populated for markdown, [] otherwise
          "title": str | None,
          "raw": str | None,           # only for kind=="html": original source
          "source_html": str | None,   # only for kind=="html": highlighted source
          "json_valid": bool,          # True for non-json, set per-file for .json
          "error": str | None,         # only for kind=="code-error"
        }
    """
    ext = _Path(filename).suffix.lower()

    # Markdown family
    if ext in {".md", ".markdown", ".mdx"}:
        r = render_markdown(text, current_file_path=current_file_path)
        return {
            "kind": "markdown",
            "html": r["html"],
            "toc": r["toc"],
            "title": r["title"],
            "raw": None,
            "source_html": None,
            "json_valid": True,
            "error": None,
        }

    # JSON: validate then highlight; on failure return code-error with message
    if ext == ".json":
        valid = True
        err = None
        try:
            _json.loads(text)
        except _json.JSONDecodeError as e:
            valid = False
            err = f"line {e.lineno} col {e.colno}: {e.msg}"
        return {
            "kind": "code" if valid else "code-error",
            "html": _render_code_view(text, "json"),
            "toc": [],
            "title": None,
            "raw": None,
            "source_html": None,
            "json_valid": valid,
            "error": err,
        }

    # Generic code view (.py)
    if ext in {".py"}:
        return {
            "kind": "code",
            "html": _render_code_view(text, "python"),
            "toc": [],
            "title": None,
            "raw": None,
            "source_html": None,
            "json_valid": True,
            "error": None,
        }

    # HTML: sandbox preview by default; raw is the original source
    if ext in {".html", ".htm"}:
        return {
            "kind": "html",
            "html": _render_html_preview(text),
            "toc": [],
            "title": None,
            "raw": text,
            "source_html": _render_code_view(text, "html"),
            "json_valid": True,
            "error": None,
        }

    # Unknown extension — fall back to plain code view
    return {
        "kind": "code",
        "html": _render_code_view(text, ""),
        "toc": [],
        "title": None,
        "raw": None,
        "source_html": None,
        "json_valid": True,
        "error": None,
    }


# === Pygments style provider ===

def get_pygments_css(theme: str) -> str:
    """Return CSS for the Pygments HtmlFormatter matching the given theme.

    ``theme`` is either "light" or "dark". Pygments built-in styles are used:
    "default" for light, "monokai" for dark. The returned CSS is scoped to
    ``.content .highlight`` because Pygments emits output wrapped in
    ``<div class="highlight"><pre>...</pre></div>`` — the ``.highlight`` class
    lives on the ``<div>``, not on ``<pre>``. This matches both fenced code
    blocks inside Markdown and standalone .py/.json/.html files.
    """
    from pygments.formatters import HtmlFormatter

    style_name = "monokai" if theme == "dark" else "default"
    formatter = HtmlFormatter(style=style_name, cssclass="highlight")
    raw = formatter.get_style_defs(".highlight")
    # Scope to the content area so the rules don't bleed into other elements
    # and ensure they win against the existing .content pre background/color.
    # Note: Pygments wraps its output in <div class="highlight"><pre>...</pre></div>
    # so we must target `.content .highlight`, not `.content pre.highlight`.
    scoped = raw.replace(".highlight", ".content .highlight")
    return scoped
