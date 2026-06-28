"""HTTP API routes."""
from __future__ import annotations

from flask import Blueprint, current_app, jsonify, request

from .config import Config
from .encoding import read_text_safe
from .render import render_markdown
from .security import ExtensionError, PathError, check_extension, resolve_safe
from .tree import list_children, search

bp = Blueprint("api", __name__, url_prefix="/api")


def _cfg() -> Config:
    return current_app.config["MDV_CONFIG"]


@bp.get("/health")
def health():
    cfg = _cfg()
    md_count = sum(
        1
        for p in cfg.root.rglob("*")
        if p.is_file() and p.suffix.lower() in cfg.content_exts
    )
    return jsonify(
        {
            "status": "ok",
            "root": str(cfg.root),
            "md_count": md_count,
        }
    )


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
            {
                "error": "file too large",
                "size": size,
                "max": cfg.max_file_size,
            }
        ), 413

    text, encoding = read_text_safe(p)
    stat = p.stat()
    meta = {
        "name": p.name,
        "path": "/" + str(p.relative_to(cfg.root)),
        "size": stat.st_size,
        "mtime": stat.st_mtime,
    }

    if fmt == "raw":
        return jsonify({"meta": meta, "text": text, "encoding": encoding})

    rendered = render_markdown(text)
    return jsonify(
        {
            "meta": meta,
            "html": rendered["html"],
            "toc": rendered["toc"],
            "title": rendered["title"],
            "encoding": encoding,
        }
    )
