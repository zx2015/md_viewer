"""Flask app factory."""
from __future__ import annotations

from flask import Flask, render_template

from .config import Config


def create_app(config: Config | None = None) -> Flask:
    cfg = config or Config.from_env()
    app = Flask(
        __name__,
        template_folder="templates",
        static_folder="static",
    )
    app.config["MDV_CONFIG"] = cfg

    # Disable caching of HTML, JS, and CSS during dev so updates are
    # picked up on plain refresh (no hard-reload required).
    @app.after_request
    def no_cache(resp):
        resp.headers["Cache-Control"] = "no-store, must-revalidate"
        resp.headers["Pragma"] = "no-cache"
        resp.headers["Expires"] = "0"
        return resp

    from .api import bp as api_bp
    app.register_blueprint(api_bp)

    @app.get("/")
    def index():
        return render_template("index.html")

    return app
