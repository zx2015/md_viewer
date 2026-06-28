# md-viewer

A lightweight, local, single-user Markdown viewer that runs in a Docker
container with a read-only mount of your notes.

- File tree (lazy-loaded), filename search, file tree filter
- GFM rendering (tables, task lists, strikethrough, autolinks)
- Wikilinks `[[name]]` and `[[name|alias]]`
- Code-block syntax highlighting with copy button
- Image rendering with error fallback
- Right-side TOC with scroll-spy
- Light / Dark / Auto theme
- Local image serving (read-only mount)
- HTML sanitization (nh3) — XSS-safe

## Quick start (Docker)

```bash
docker run -d --name md-viewer -p 8000:8000 \
  -v /path/to/your/notes:/data:ro \
  md-viewer:latest
```

Open http://localhost:8000.

> Build the image first: `docker build -t md-viewer:latest .`
> Or use compose: edit `docker-compose.yml` to point at your notes path, then `docker compose up -d`.

The mounted directory must be **read-only** (`:ro`). The application also
validates all paths internally to prevent `../` escape.

## Quick start (development, no Docker)

```bash
# Use the shared virtualenv
/media/data/venv/bin/pip install -e ".[dev]"

# Run with local samples
MDV_ROOT=./samples /media/data/venv/bin/python -m md_viewer serve

# Run tests
/media/data/venv/bin/pytest
```

## Configuration

All config via environment variables (or `--root`, `--port`, `--host` flags):

| Variable | Default | Description |
|----------|---------|-------------|
| `MDV_ROOT` | `/data` | Directory to serve |
| `MDV_HOST` | `0.0.0.0` | Bind host |
| `MDV_PORT` | `8000` | Bind port |
| `MDV_MAX_FILE_SIZE` | `5242880` (5 MB) | Max file size in bytes |

CLI: `python -m md_viewer serve --root ~/notes --port 9000`.

## Keyboard shortcuts

| Keys | Action |
|------|--------|
| `J` / `K` | Previous / next `.md` |
| `Ctrl+K` | Focus search box |
| `Ctrl+B` | Toggle sidebar |
| `Ctrl+Shift+L` | Cycle theme (auto → dark → light) |
| `Ctrl+R` | Refresh current file |
| `R` | Toggle Raw / Rendered |
| `?` | Show shortcuts panel |
| `Esc` | Close panel / clear search |

## Architecture

```
Browser (vanilla JS)
   ↕ HTTP (JSON + images)
Flask (single process, non-root)
   ↕ read-only
Mounted directory (/data)
```

- Backend: Flask 3 + markdown-it-py + nh3 (XSS sanitizer) + pygments
- Frontend: zero-build vanilla JS + CSS variables for theming
- Security: path whitelist + ext whitelist + sanitized HTML + read-only mount

See [`docs/2026-06-28-md-viewer-design.md`](docs/2026-06-28-md-viewer-design.md)
for the full design and [`docs/2026-06-28-md-viewer-impl-plan.md`](docs/2026-06-28-md-viewer-impl-plan.md)
for the implementation plan.

## Project layout

```
src/md_viewer/
  __init__.py      package marker
  __main__.py      python -m md_viewer entry
  cli.py           argparse subcommands
  config.py        env-based config dataclass
  security.py      path/extension validation
  encoding.py      UTF-8 → GB18030 → latin-1 fallback
  tree.py          directory listing + filename search
  render.py        markdown-it-py + plugins + nh3 sanitization
  server.py        Flask app factory
  api.py           /api/* routes
  templates/       Jinja2 HTML
  static/          CSS, JS
tests/             pytest
samples/           .md examples
docs/              design + implementation plan
```

## Scope (v1)

In scope: file tree, search, render, theme, image, wikilinks, GFM, code highlight, sanitization.

Out of scope (deferred): full-text search, tags/categories, backlinks, multi-root mounts, mobile layout, HTTPS, edit/preview.
