"""Command-line interface."""
from __future__ import annotations

import argparse
from pathlib import Path

from .config import Config
from .server import create_app


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="md-viewer", description="Markdown viewer")
    sub = p.add_subparsers(dest="command", required=True)

    serve = sub.add_parser("serve", help="Start the web server")
    serve.add_argument("--host", default=None, help="Bind host (default from MDV_HOST or 0.0.0.0)")
    serve.add_argument("--port", type=int, default=None, help="Bind port (default from MDV_PORT or 8000)")
    serve.add_argument("--root", type=Path, default=None, help="Root directory (default from MDV_ROOT or /data)")
    serve.add_argument("--debug", action="store_true", help="Enable Flask debug mode")

    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "serve":
        env_cfg = Config.from_env()
        cfg = Config(
            root=(args.root or env_cfg.root).resolve(),
            host=args.host or env_cfg.host,
            port=args.port if args.port is not None else env_cfg.port,
            max_file_size=env_cfg.max_file_size,
        )
        app = create_app(cfg)
        app.run(host=cfg.host, port=cfg.port, debug=args.debug)
        return 0

    parser.print_help()
    return 2
