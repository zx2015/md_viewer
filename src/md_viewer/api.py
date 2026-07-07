"""HTTP API routes."""
from __future__ import annotations

import mimetypes

from flask import Blueprint, current_app, jsonify, request, send_file

from .config import Config
from .encoding import read_text_safe
from .render import get_pygments_css, render_viewable
from .security import ExtensionError, PathError, check_extension, resolve_safe
from .tree import list_children, search

bp = Blueprint("api", __name__, url_prefix="/api")


def _cfg() -> Config:
    return current_app.config["MDV_CONFIG"]


@bp.get("/health")
def health():
    # Lightweight liveness probe — must be cheap.
    # We intentionally do NOT rglob the root here; that was too slow
    # when the root contains a large number of files (e.g. multiple git
    # repos or a notes tree with thousands of files).
    return jsonify({"status": "ok"})


@bp.get("/tree")
def get_tree():
    cfg = _cfg()
    try:
        node = list_children("/", cfg)
        return jsonify(node)
    except PathError as e:
        return jsonify({"error": str(e)}), 403
    except (FileNotFoundError, NotADirectoryError) as e:
        return jsonify({"error": str(e)}), 404


@bp.get("/children")
def get_children():
    cfg = _cfg()
    path = request.args.get("path", "/")
    try:
        node = list_children(path, cfg)
        return jsonify(node)
    except PathError as e:
        return jsonify({"error": str(e)}), 403
    except (FileNotFoundError, NotADirectoryError) as e:
        return jsonify({"error": str(e)}), 404


@bp.get("/search")
def get_search():
    cfg = _cfg()
    q = request.args.get("q", "").strip()
    limit = max(1, min(int(request.args.get("limit", "50")), 200))
    matches = search(q, cfg, limit=limit) if q else []
    return jsonify({"query": q, "matches": matches})


@bp.get("/file")
def get_file():
    cfg = _cfg()
    path = request.args.get("path", "")
    fmt = request.args.get("format", "rendered")

    try:
        p = resolve_safe(path, cfg.root)
        check_extension(p, cfg.content_exts)
    except PathError as e:
        return jsonify({"error": str(e)}), 403
    except ExtensionError as e:
        return jsonify({"error": str(e)}), 400

    if not p.is_file():
        return jsonify({"error": "not found"}), 404

    size = p.stat().st_size
    if size > cfg.max_file_size:
        return jsonify(
            {"error": "file too large", "size": size, "max": cfg.max_file_size}
        ), 413

    text, encoding = read_text_safe(p)
    stat = p.stat()
    meta = {
        "name": p.name,
        "path": "/" + str(p.relative_to(cfg.root)),
        "size": stat.st_size,
        "mtime": stat.st_mtime,
    }

    rendered = render_viewable(p.name, text, current_file_path=meta["path"])

    # Markdown: format=raw returns the raw markdown text in `text` for v1
    # frontend backward compatibility.
    if rendered["kind"] == "markdown" and fmt == "raw":
        return jsonify(
            {"meta": meta, "text": text, "encoding": encoding, "kind": "markdown"}
        )

    # HTML: format=raw swaps the primary HTML to the highlighted source so
    # the frontend can render it without a second roundtrip.
    if rendered["kind"] == "html" and fmt == "raw":
        return jsonify(
            {
                "meta": meta,
                "kind": "html",
                "html": rendered["source_html"],
                "raw": rendered["raw"],
                "title": None,
                "encoding": encoding,
            }
        )

    return jsonify(
        {
            "meta": meta,
            "kind": rendered["kind"],
            "html": rendered["html"],
            "toc": rendered.get("toc") or [],
            "title": rendered.get("title"),
            "encoding": encoding,
            "raw": rendered.get("raw"),
            "source_html": rendered.get("source_html"),
            "json_valid": rendered.get("json_valid", True),
            "error": rendered.get("error"),
        }
    )


@bp.get("/image")
def get_image():
    cfg = _cfg()
    path = request.args.get("path", "")

    try:
        p = resolve_safe(path, cfg.root)
        check_extension(p, cfg.image_exts)
    except PathError as e:
        return jsonify({"error": str(e)}), 403
    except ExtensionError as e:
        return jsonify({"error": str(e)}), 400

    if not p.is_file():
        return jsonify({"error": "not found"}), 404

    stat = p.stat()
    if stat.st_size > cfg.max_file_size:
        return jsonify({"error": "image too large"}), 413

    etag = f'"{stat.st_mtime_ns:x}-{stat.st_size:x}"'
    if request.headers.get("If-None-Match") == etag:
        return "", 304

    mime, _ = mimetypes.guess_type(str(p))
    resp = send_file(
        str(p),
        mimetype=mime or "application/octet-stream",
        conditional=True,
    )
    resp.headers["ETag"] = etag
    return resp


@bp.get("/code-style")
def get_code_style():
    """Return Pygments-formatter CSS for the requested theme.

    ``theme`` is "light" or "dark"; anything else (including missing) falls
    back to "light". The response is text/css with a far-future Cache-Control
    so the browser only fetches once per theme per session.
    """
    from flask import make_response

    theme = (request.args.get("theme") or "light").lower()
    if theme not in {"light", "dark"}:
        theme = "light"
    css = get_pygments_css(theme)
    resp = make_response(css, 200)
    resp.headers["Content-Type"] = "text/css; charset=utf-8"
    # Cache for a day; client also re-fetches on theme switch.
    resp.headers["Cache-Control"] = "public, max-age=86400"
    return resp
