"""HTTP API routes."""
from __future__ import annotations

from flask import Blueprint, current_app, jsonify, request

from .config import Config
from .security import PathError
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
