"""HTTP API routes."""
from __future__ import annotations

from flask import Blueprint, current_app, jsonify

from .config import Config

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
