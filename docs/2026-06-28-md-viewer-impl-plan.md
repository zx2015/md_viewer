# md-viewer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Docker-deployable Markdown viewer per `docs/2026-06-28-md-viewer-design.md` (Flask + vanilla JS, read-only mount, lazy file tree, GFM + wikilinks + KaTeX + Mermaid).

**Architecture:** Single Flask process serves JSON API + static frontend. File tree lazily traversed on demand; search is server-side full scan. Markdown rendered with `markdown-it-py` + plugins, sanitized with `nh3`. KaTeX/Mermaid bundled locally under `static/vendor/` (downloaded at Docker build time). Frontend is single vanilla JS file with no build step.

**Tech Stack:** Python 3.12, Flask 3, markdown-it-py, mdit-py-plugins, nh3, pygments, pytest. Vanilla JS + KaTeX + Mermaid in browser.

---

## File Structure

```
md-viewer/
├── AGENTS.md
├── README.md
├── requirements.txt
├── requirements-dev.txt
├── pytest.ini
├── pyproject.toml
├── .gitignore
├── .dockerignore
├── Dockerfile
├── docker-compose.yml
├── src/
│   └── md_viewer/
│       ├── __init__.py
│       ├── __main__.py
│       ├── cli.py
│       ├── config.py
│       ├── security.py
│       ├── encoding.py
│       ├── tree.py
│       ├── render.py
│       ├── server.py
│       ├── api.py
│       ├── templates/index.html
│       └── static/
│           ├── app.js
│           ├── style.css
│           └── vendor/        # KaTeX + Mermaid (downloaded at build time)
├── tests/
│   ├── conftest.py
│   ├── test_config.py
│   ├── test_security.py
│   ├── test_encoding.py
│   ├── test_tree.py
│   ├── test_render.py
│   ├── test_api.py
│   └── test_cli.py
├── samples/
│   ├── basic.md
│   ├── gfm.md
│   ├── wikilinks.md
│   ├── math.md
│   ├── mermaid.md
│   ├── code.md
│   ├── frontmatter.md
│   ├── images.md
│   └── assets/sample.png
└── docs/
    ├── 2026-06-28-md-viewer-design.md
    └── 2026-06-28-md-viewer-impl-plan.md
```

**Module responsibilities** (one job each):
- `config.py`: read env vars into a typed config object
- `security.py`: path validation (no `..` escape, ext whitelist)
- `encoding.py`: read file with UTF-8 → GB18030 → latin-1 fallback
- `tree.py`: list directory children, search by filename, sort (dirs first)
- `render.py`: markdown → HTML pipeline (preprocess wikilinks → md-it-py → sanitize)
- `server.py`: Flask app factory
- `api.py`: route handlers (thin, delegate to modules above)
- `cli.py`: argparse subcommands
- `__main__.py`: invoke cli

---

## Phase 0 — Project Scaffolding

### Task 0.1: Initialize git repo and .gitignore

**Files:**
- Create: `.gitignore`

- [ ] **Step 1: Initialize git**

Run: `git init`
Expected: `Initialized empty Git repository in /media/data/git/md-viewer/.git/`

- [ ] **Step 2: Write `.gitignore`**

```gitignore
# Python
__pycache__/
*.py[cod]
*.egg-info/
.venv/
venv/

# Local knowledge base (global convention)
.learnings/

# OpenCode runtime (global convention)
.OpenCode/

# Editor / OS
.vscode/
.idea/
.DS_Store
*.swp

# Vendored deps (regenerated at build, not committed)
src/md_viewer/static/vendor/

# Test artifacts
.pytest_cache/
.coverage
htmlcov/

# User-personal sample notes (do not commit)
samples/assets/personal-*/
```

- [ ] **Step 3: Configure git user (if not already global)**

Run: `git config user.email "md-viewer@local" && git config user.name "md-viewer"`

- [ ] **Step 4: Commit**

```bash
cd /media/data/git/md-viewer
git add .gitignore AGENTS.md docs/
git commit -m "chore: initialize repo with .gitignore, AGENTS.md and design doc"
```

### Task 0.2: Create directory structure and pyproject.toml

**Files:**
- Create: `pyproject.toml`
- Create: empty `src/md_viewer/`, `src/md_viewer/templates/`, `src/md_viewer/static/`, `tests/`, `samples/`, `samples/assets/`

- [ ] **Step 1: Create dirs**

Run:
```bash
mkdir -p src/md_viewer/templates src/md_viewer/static tests samples/assets
```

- [ ] **Step 2: Write `pyproject.toml`**

```toml
[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[project]
name = "md-viewer"
version = "0.1.0"
description = "Local Markdown viewer served from a Docker container"
requires-python = ">=3.12"
dependencies = [
    "Flask==3.0.3",
    "markdown-it-py==3.0.0",
    "mdit-py-plugins==0.4.2",
    "nh3==0.2.20",
    "pygments==2.18.0",
]

[project.optional-dependencies]
dev = [
    "pytest==8.3.3",
    "pytest-cov==5.0.0",
]

[tool.setuptools.packages.find]
where = ["src"]

[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "-ra --strict-markers"
```

- [ ] **Step 3: Add package marker**

Write `src/md_viewer/__init__.py`:
```python
__version__ = "0.1.0"
```

- [ ] **Step 4: Install package in editable mode**

Run: `/media/data/venv/bin/pip install -e ".[dev]"`
Expected: `Successfully installed md-viewer-0.1.0 ...`

- [ ] **Step 5: Verify imports**

Run: `/media/data/venv/bin/python -c "import flask, markdown_it, mdit_py_plugins, nh3, pygments; print('ok')"`
Expected: `ok`

- [ ] **Step 6: Commit**

```bash
git add pyproject.toml src/ tests/ samples/
git commit -m "chore: package scaffolding with pyproject.toml"
```

### Task 0.3: Add pytest config (already in pyproject) and verify

- [ ] **Step 1: Run pytest to verify infrastructure works**

Run: `/media/data/venv/bin/pytest --collect-only`
Expected: `no tests ran` (or similar — we have no tests yet).

---

## Phase 1 — Backend Foundation (TDD)

### Task 1.1: config.py — env-based config

**Files:**
- Create: `src/md_viewer/config.py`
- Create: `tests/test_config.py`

- [ ] **Step 1: Write failing test**

Write `tests/test_config.py`:
```python
from md_viewer.config import Config


def test_default_root(monkeypatch, tmp_path):
    monkeypatch.setenv("MDV_ROOT", str(tmp_path))
    cfg = Config.from_env()
    assert cfg.root == tmp_path.resolve()


def test_default_port(monkeypatch, tmp_path):
    monkeypatch.setenv("MDV_ROOT", str(tmp_path))
    monkeypatch.delenv("MDV_PORT", raising=False)
    cfg = Config.from_env()
    assert cfg.port == 8000


def test_custom_port(monkeypatch, tmp_path):
    monkeypatch.setenv("MDV_ROOT", str(tmp_path))
    monkeypatch.setenv("MDV_PORT", "9000")
    cfg = Config.from_env()
    assert cfg.port == 9000


def test_max_file_size_default(monkeypatch, tmp_path):
    monkeypatch.setenv("MDV_ROOT", str(tmp_path))
    cfg = Config.from_env()
    assert cfg.max_file_size == 5 * 1024 * 1024


def test_content_exts():
    assert ".md" in Config.content_exts
    assert ".markdown" in Config.content_exts
    assert ".mdx" in Config.content_exts


def test_image_exts():
    assert ".png" in Config.image_exts
    assert ".svg" in Config.image_exts
```

- [ ] **Step 2: Run test to verify failure**

Run: `/media/data/venv/bin/pytest tests/test_config.py -v`
Expected: `ModuleNotFoundError: No module named 'md_viewer.config'`

- [ ] **Step 3: Implement**

Write `src/md_viewer/config.py`:
```python
"""Runtime configuration loaded from environment variables."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class Config:
    root: Path
    host: str = "0.0.0.0"
    port: int = 8000
    max_file_size: int = 5 * 1024 * 1024

    content_exts: frozenset[str] = field(
        default_factory=lambda: frozenset({".md", ".markdown", ".mdx"})
    )
    image_exts: frozenset[str] = field(
        default_factory=lambda: frozenset(
            {".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg"}
        )
    )

    @classmethod
    def from_env(cls) -> "Config":
        return cls(
            root=Path(os.environ.get("MDV_ROOT", "/data")).resolve(),
            host=os.environ.get("MDV_HOST", "0.0.0.0"),
            port=int(os.environ.get("MDV_PORT", "8000")),
            max_file_size=int(
                os.environ.get("MDV_MAX_FILE_SIZE", str(5 * 1024 * 1024))
            ),
        )
```

- [ ] **Step 4: Run test to verify pass**

Run: `/media/data/venv/bin/pytest tests/test_config.py -v`
Expected: 6 passed.

- [ ] **Step 5: Commit**

```bash
git add src/md_viewer/config.py tests/test_config.py
git commit -m "feat(config): add env-based Config with content/image ext whitelist"
```

### Task 1.2: security.py — path validation + ext whitelist

**Files:**
- Create: `src/md_viewer/security.py`
- Create: `tests/test_security.py`

- [ ] **Step 1: Write failing test**

Write `tests/test_security.py`:
```python
import pytest

from md_viewer.security import (
    resolve_safe,
    check_extension,
    PathError,
    ExtensionError,
)


def test_resolve_safe_relative(tmp_path):
    (tmp_path / "a.md").write_text("x")
    p = resolve_safe("/a.md", tmp_path)
    assert p == (tmp_path / "a.md").resolve()


def test_resolve_safe_absolute_inside(tmp_path):
    (tmp_path / "a.md").write_text("x")
    p = resolve_safe(str((tmp_path / "a.md").resolve()), tmp_path)
    assert p == (tmp_path / "a.md").resolve()


def test_resolve_safe_blocks_parent_escape(tmp_path):
    outside = tmp_path.parent / "secret.md"
    outside.write_text("secret")
    with pytest.raises(PathError):
        resolve_safe(f"../{outside.name}", tmp_path)


def test_resolve_safe_blocks_absolute_outside(tmp_path):
    with pytest.raises(PathError):
        resolve_safe("/etc/passwd", tmp_path)


def test_check_extension_allowed(tmp_path):
    f = tmp_path / "a.md"
    f.write_text("")
    check_extension(f, {".md", ".markdown"})


def test_check_extension_rejected(tmp_path):
    f = tmp_path / "a.exe"
    f.write_text("")
    with pytest.raises(ExtensionError):
        check_extension(f, {".md"})


def test_check_extension_case_insensitive(tmp_path):
    f = tmp_path / "A.MD"
    f.write_text("")
    check_extension(f, {".md"})
```

- [ ] **Step 2: Run test to verify failure**

Run: `/media/data/venv/bin/pytest tests/test_security.py -v`
Expected: `ModuleNotFoundError: No module named 'md_viewer.security'`

- [ ] **Step 3: Implement**

Write `src/md_viewer/security.py`:
```python
"""Path and extension validation. Defense against ../ escape and bad inputs."""
from __future__ import annotations

from pathlib import Path


class PathError(ValueError):
    """Raised when a path resolves outside the allowed root."""


class ExtensionError(ValueError):
    """Raised when a file extension is not in the whitelist."""


def resolve_safe(path_str: str, root: Path) -> Path:
    """Resolve a user-provided path against ``root``.

    Accepts both relative paths (resolved against ``root``) and absolute paths
    that must be inside ``root`` after resolution. Raises ``PathError`` if
    the resolved path escapes ``root``.
    """
    if not path_str:
        raise PathError("Empty path")
    p = Path(path_str)
    if not p.is_absolute():
        p = (root / p).resolve()
    else:
        p = p.resolve()
    try:
        p.relative_to(root)
    except ValueError as e:
        raise PathError(f"Path {p} escapes root {root}") from e
    return p


def check_extension(path: Path, allowed: set[str] | frozenset[str]) -> None:
    """Raise ``ExtensionError`` if path's suffix is not in ``allowed``."""
    suffix = path.suffix.lower()
    if suffix not in allowed:
        raise ExtensionError(f"Extension {suffix!r} not in {sorted(allowed)}")
```

- [ ] **Step 4: Run test to verify pass**

Run: `/media/data/venv/bin/pytest tests/test_security.py -v`
Expected: 7 passed.

- [ ] **Step 5: Commit**

```bash
git add src/md_viewer/security.py tests/test_security.py
git commit -m "feat(security): add path resolution + extension whitelist"
```

### Task 1.3: encoding.py — UTF-8 / GB18030 / latin-1 fallback

**Files:**
- Create: `src/md_viewer/encoding.py`
- Create: `tests/test_encoding.py`

- [ ] **Step 1: Write failing test**

Write `tests/test_encoding.py`:
```python
from md_viewer.encoding import read_text_safe


def test_utf8(tmp_path):
    f = tmp_path / "a.md"
    f.write_bytes("你好 world".encode("utf-8"))
    text, enc = read_text_safe(f)
    assert text == "你好 world"
    assert enc == "utf-8"


def test_gb18030_fallback(tmp_path):
    f = tmp_path / "a.md"
    f.write_bytes("你好".encode("gb18030"))
    text, enc = read_text_safe(f)
    assert text == "你好"
    assert enc == "gb18030"


def test_latin1_fallback(tmp_path):
    f = tmp_path / "a.md"
    f.write_bytes(b"\xe9\xe8")  # invalid utf-8, valid latin-1 ('é','è')
    text, enc = read_text_safe(f)
    assert text == "éè"
    assert enc == "latin-1"


def test_full_byte_range(tmp_path):
    f = tmp_path / "a.md"
    f.write_bytes(bytes(range(256)))
    text, enc = read_text_safe(f)
    assert enc == "latin-1"
    assert len(text) == 256
```

- [ ] **Step 2: Run test to verify failure**

Run: `/media/data/venv/bin/pytest tests/test_encoding.py -v`
Expected: `ModuleNotFoundError: No module named 'md_viewer.encoding'`

- [ ] **Step 3: Implement**

Write `src/md_viewer/encoding.py`:
```python
"""Read text files with encoding fallback.

Order: UTF-8 → GB18030 → latin-1. latin-1 always succeeds because every byte
0x00-0xFF maps to a valid code point, so it is the final fallback rather than
an error.
"""
from __future__ import annotations

from pathlib import Path

_FALLBACK_ENCODINGS: tuple[str, ...] = ("utf-8", "gb18030", "latin-1")


def read_text_safe(path: Path) -> tuple[str, str]:
    raw = path.read_bytes()
    for enc in _FALLBACK_ENCODINGS:
        try:
            return raw.decode(enc), enc
        except UnicodeDecodeError:
            continue
    raise UnicodeDecodeError(
        "encoding-fallback",
        raw,
        0,
        len(raw),
        f"could not decode {path} with any of {_FALLBACK_ENCODINGS}",
    )
```

- [ ] **Step 4: Run test to verify pass**

Run: `/media/data/venv/bin/pytest tests/test_encoding.py -v`
Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add src/md_viewer/encoding.py tests/test_encoding.py
git commit -m "feat(encoding): UTF-8 → GB18030 → latin-1 fallback reader"
```

---

### Task 1.4: tree.py — directory listing

**Files:**
- Create: `src/md_viewer/tree.py`
- Create: `tests/conftest.py`
- Create: `tests/test_tree.py`

- [ ] **Step 1: Write conftest helper**

Write `tests/conftest.py`:
```python
import pytest
from md_viewer.config import Config


@pytest.fixture
def cfg(tmp_path):
    return Config(root=tmp_path.resolve())


@pytest.fixture
def sample_tree(tmp_path):
    """Build a small directory tree:

    /a.md
    /b.txt          (non-content, not listed)
    /docs/c.md
    /docs/d.md
    /docs/sub/e.md
    /empty/         (empty dir)
    """
    (tmp_path / "a.md").write_text("")
    (tmp_path / "b.txt").write_text("")
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "c.md").write_text("")
    (docs / "d.md").write_text("")
    sub = docs / "sub"
    sub.mkdir()
    (sub / "e.md").write_text("")
    (tmp_path / "empty").mkdir()
    return tmp_path


@pytest.fixture
def root_path(sample_tree):
    return sample_tree.resolve()
```

- [ ] **Step 2: Write failing test**

Write `tests/test_tree.py`:
```python
import pytest

from md_viewer.tree import list_children, search, to_api_path


def test_to_api_path_root(root_path):
    assert to_api_path(root_path, root_path) == "/"


def test_to_api_path_subdir(root_path):
    sub = root_path / "docs"
    assert to_api_path(sub, root_path) == "/docs"


def test_list_children_root(sample_tree, cfg):
    node = list_children("/", cfg)
    assert node["path"] == "/"
    assert node["type"] == "dir"
    names = [c["name"] for c in node["children"]]
    assert "a.md" in names
    assert "b.txt" not in names
    assert "docs" in names
    assert "empty" in names


def test_list_children_dirs_first(sample_tree, cfg):
    node = list_children("/", cfg)
    types = [c["type"] for c in node["children"]]
    dir_indices = [i for i, t in enumerate(types) if t == "dir"]
    file_indices = [i for i, t in enumerate(types) if t == "file"]
    if dir_indices and file_indices:
        assert max(dir_indices) < min(file_indices)


def test_list_children_alphabetical_within_type(sample_tree, cfg):
    node = list_children("/", cfg)
    files = [c["name"] for c in node["children"] if c["type"] == "file"]
    assert files == sorted(files, key=str.lower)


def test_list_children_subdir(sample_tree, cfg):
    node = list_children("/docs", cfg)
    names = [c["name"] for c in node["children"]]
    assert names == ["c.md", "d.md", "sub"]


def test_list_children_has_children(sample_tree, cfg):
    node = list_children("/", cfg)
    docs = next(c for c in node["children"] if c["name"] == "docs")
    assert docs["has_children"] is True
    assert docs["child_count"] == 3


def test_list_children_empty_dir_has_no_children(sample_tree, cfg):
    node = list_children("/", cfg)
    empty = next(c for c in node["children"] if c["name"] == "empty")
    assert empty["has_children"] is False
    assert empty["child_count"] == 0


def test_list_children_missing_dir_raises(sample_tree, cfg):
    with pytest.raises(FileNotFoundError):
        list_children("/nope", cfg)
```

- [ ] **Step 3: Run test to verify failure**

Run: `/media/data/venv/bin/pytest tests/test_tree.py -v`
Expected: `ModuleNotFoundError: No module named 'md_viewer.tree'`

- [ ] **Step 4: Implement**

Write `src/md_viewer/tree.py`:
```python
"""File tree: directory listing and filename search."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path

from .config import Config
from .security import resolve_safe


@dataclass
class TreeNode:
    name: str
    path: str
    type: str  # "dir" | "file"
    has_children: bool = False
    child_count: int = 0
    size: int = 0
    children: list["TreeNode"] = field(default_factory=list)

    def to_dict(self) -> dict:
        d = asdict(self)
        d.pop("children", None)
        if self.children:
            d["children"] = [c.to_dict() for c in self.children]
        return d


def to_api_path(p: Path, root: Path) -> str:
    rel = p.relative_to(root)
    return "/" if str(rel) == "." else "/" + str(rel)


def _build_node(path: Path, name: str, root: Path) -> TreeNode:
    if path.is_dir():
        children = list(path.iterdir())
        return TreeNode(
            name=name,
            path=to_api_path(path, root),
            type="dir",
            has_children=len(children) > 0,
            child_count=len(children),
        )
    stat = path.stat()
    return TreeNode(
        name=name,
        path=to_api_path(path, root),
        type="file",
        size=stat.st_size,
    )


def _sort_key(n: TreeNode):
    return (0 if n.type == "dir" else 1, n.name.lower())


def list_children(path_str: str, cfg: Config) -> dict:
    """List one level of the directory at ``path_str`` relative to cfg.root."""
    p = resolve_safe(path_str, cfg.root)
    if not p.exists():
        raise FileNotFoundError(path_str)
    if not p.is_dir():
        raise NotADirectoryError(path_str)

    children: list[TreeNode] = []
    for entry in p.iterdir():
        children.append(_build_node(entry, entry.name, cfg.root))
    # filter out non-content files at non-root levels too
    children = [
        c for c in children
        if c.type == "dir" or (c.size or True) and any(
            entry.suffix.lower() in cfg.content_exts
            for entry in [p / c.name]
        )
    ]
    children.sort(key=_sort_key)

    node = TreeNode(
        name=p.name or "data",
        path=to_api_path(p, cfg.root),
        type="dir",
        children=children,
        has_children=bool(children),
        child_count=len(children),
    )
    return node.to_dict()
```

**Note**: the comprehension above is a bit awkward; replace the children-filter block with the cleaner version below.

Replace the children-filter block in `list_children`:
```python
    children: list[TreeNode] = []
    for entry in p.iterdir():
        if entry.is_dir():
            children.append(_build_node(entry, entry.name, cfg.root))
        elif entry.suffix.lower() in cfg.content_exts:
            children.append(_build_node(entry, entry.name, cfg.root))
    children.sort(key=_sort_key)
```

- [ ] **Step 5: Run test to verify pass**

Run: `/media/data/venv/bin/pytest tests/test_tree.py -v`
Expected: 9 passed.

- [ ] **Step 6: Commit**

```bash
git add src/md_viewer/tree.py tests/test_tree.py tests/conftest.py
git commit -m "feat(tree): one-level directory listing with dirs-first sort"
```

### Task 1.5: tree.py — filename search

**Files:**
- Modify: `src/md_viewer/tree.py`
- Modify: `tests/test_tree.py`

- [ ] **Step 1: Add failing tests**

Append to `tests/test_tree.py`:
```python
def test_search_no_match(sample_tree, cfg):
    assert search("readme", cfg) == []


def test_search_finds_file(sample_tree, cfg):
    paths = [r["path"] for r in search("a", cfg)]
    assert "/a.md" in paths


def test_search_case_insensitive(sample_tree, cfg):
    paths = [r["path"] for r in search("A.MD", cfg)]
    assert "/a.md" in paths


def test_search_recursive(sample_tree, cfg):
    paths = [r["path"] for r in search("e", cfg)]
    assert "/docs/sub/e.md" in paths


def test_search_excludes_non_content(sample_tree, cfg):
    assert search("b", cfg) == []


def test_search_limit(sample_tree, cfg):
    for i in range(5):
        (sample_tree / f"x{i}.md").write_text("")
    assert len(search("x", cfg, limit=2)) == 2


def test_search_relevance(sample_tree, cfg):
    (sample_tree / "notes.md").write_text("")
    (sample_tree / "notes-extra.md").write_text("")
    results = search("notes.md", cfg)
    assert results[0]["name"] == "notes.md"
```

- [ ] **Step 2: Run to verify failure**

Run: `/media/data/venv/bin/pytest tests/test_tree.py::test_search_no_match -v`
Expected: `ImportError: cannot import name 'search'`

- [ ] **Step 3: Implement search**

Append to `src/md_viewer/tree.py`:
```python
def search(query: str, cfg: Config, limit: int = 50) -> list[dict]:
    """Recursively search filenames (case-insensitive substring).

    Scoring (higher = more relevant):
      100  exact filename match (case-insensitive)
       50  filename starts with query
       10  filename contains query
    """
    if not query.strip():
        return []
    q_lower = query.lower()

    matches: list[tuple[int, dict]] = []

    def visit(p: Path):
        try:
            entries = list(p.iterdir())
        except (PermissionError, OSError):
            return
        for entry in entries:
            if entry.is_dir():
                visit(entry)
                continue
            if entry.suffix.lower() not in cfg.content_exts:
                continue
            name_lower = entry.name.lower()
            score = 0
            if name_lower == q_lower:
                score = 100
            elif name_lower.startswith(q_lower):
                score = 50
            elif q_lower in name_lower:
                score = 10
            if score > 0:
                matches.append((score, _build_node(entry, entry.name, cfg.root).to_dict()))

    visit(cfg.root)
    matches.sort(key=lambda x: (-x[0], x[1]["name"].lower()))
    return [m for _, m in matches[:limit]]
```

- [ ] **Step 4: Run to verify pass**

Run: `/media/data/venv/bin/pytest tests/test_tree.py -v`
Expected: 16 passed.

- [ ] **Step 5: Commit**

```bash
git add src/md_viewer/tree.py tests/test_tree.py
git commit -m "feat(tree): recursive filename search with relevance scoring"
```

---

## Phase 2 — Rendering Pipeline (TDD)

### Task 2.1: render.py — core markdown + TOC

**Files:**
- Create: `src/md_viewer/render.py`
- Create: `tests/test_render.py`

- [ ] **Step 1: Write failing test**

Write `tests/test_render.py`:
```python
from md_viewer.render import render_markdown


def test_basic_paragraph():
    r = render_markdown("hello world")
    assert "<p>hello world</p>" in r["html"]


def test_h1_has_id():
    r = render_markdown("# Title")
    assert '<h1 id="title">Title</h1>' in r["html"]


def test_h2_has_id():
    r = render_markdown("## Sub")
    assert '<h2 id="sub">Sub</h2>' in r["html"]


def test_emphasis():
    r = render_markdown("**bold** *italic*")
    assert "<strong>bold</strong>" in r["html"]
    assert "<em>italic</em>" in r["html"]


def test_code_inline():
    r = render_markdown("`code`")
    assert "<code>code</code>" in r["html"]


def test_returns_required_keys():
    r = render_markdown("# X\nbody")
    assert "html" in r
    assert "toc" in r
    assert "title" in r
    assert isinstance(r["toc"], list)


def test_title_from_first_h1():
    r = render_markdown("# First\n## Second\n# Third")
    assert r["title"] == "First"


def test_toc_includes_levels_1_to_3():
    r = render_markdown("# H1\n## H2\n### H3\n#### H4")
    assert len(r["toc"]) == 3
    levels = [t["level"] for t in r["toc"]]
    assert levels == [1, 2, 3]
```

- [ ] **Step 2: Run to verify failure**

Run: `/media/data/venv/bin/pytest tests/test_render.py -v`
Expected: `ModuleNotFoundError: No module named 'md_viewer.render'`

- [ ] **Step 3: Implement**

Write `src/md_viewer/render.py`:
```python
"""Markdown → HTML rendering pipeline."""
from __future__ import annotations

from markdown_it import MarkdownIt

_md = MarkdownIt("commonmark", {"html": True, "linkify": True, "typographer": True})
_md.enable(["replacements", "smartquotes"])


def render_markdown(text: str) -> dict:
    """Render markdown to HTML and extract TOC + title."""
    tokens = _md.parse(text)
    html = _md.render(text)

    toc: list[dict] = []
    title: str | None = None
    in_heading = False
    current_level = 0
    current_id: str | None = None
    current_text: list[str] = []

    for tok in tokens:
        if tok.type == "heading_open":
            in_heading = True
            current_level = int(tok.tag[1])
            current_id = tok.attrGet("id")
            current_text = []
        elif tok.type == "heading_close":
            if current_level <= 3:
                heading_text = "".join(current_text).strip()
                toc.append(
                    {"level": current_level, "text": heading_text, "id": current_id}
                )
                if current_level == 1 and title is None:
                    title = heading_text
            in_heading = False
        elif in_heading and tok.type == "inline":
            current_text.append(tok.content)
            for child in tok.children or []:
                if child.type == "text":
                    current_text.append(child.content)

    return {"html": html, "toc": toc, "title": title}
```

- [ ] **Step 4: Run to verify pass**

Run: `/media/data/venv/bin/pytest tests/test_render.py -v`
Expected: 8 passed.

- [ ] **Step 5: Commit**

```bash
git add src/md_viewer/render.py tests/test_render.py
git commit -m "feat(render): core markdown-it-py rendering with TOC extraction"
```

### Task 2.2: render.py — GFM (tables, task lists, strikethrough) + plugins

**Files:**
- Modify: `src/md_viewer/render.py`
- Modify: `tests/test_render.py`

- [ ] **Step 1: Add failing tests**

Append to `tests/test_render.py`:
```python
def test_gfm_table():
    md = "| a | b |\n|---|\n| 1 | 2 |"
    r = render_markdown(md)
    assert "<table>" in r["html"]
    assert "<td>1</td>" in r["html"]


def test_gfm_task_checked():
    md = "- [x] done\n- [ ] todo"
    r = render_markdown(md)
    assert 'type="checkbox"' in r["html"]
    assert "checked" in r["html"]


def test_gfm_strikethrough():
    r = render_markdown("~~gone~~")
    assert "<s>gone</s>" in r["html"]


def test_gfm_autolink():
    r = render_markdown("Visit https://example.com today")
    assert '<a href="https://example.com"' in r["html"]
```

- [ ] **Step 2: Run to verify failure**

Run: `/media/data/venv/bin/pytest tests/test_render.py::test_gfm_table -v`
Expected: FAIL (no table support).

- [ ] **Step 3: Enable plugins**

Replace the top of `src/md_viewer/render.py` (the `_md` setup) with:
```python
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
```

- [ ] **Step 4: Run to verify pass**

Run: `/media/data/venv/bin/pytest tests/test_render.py -v`
Expected: 12 passed.

- [ ] **Step 5: Commit**

```bash
git add src/md_viewer/render.py tests/test_render.py
git commit -m "feat(render): enable GFM tables, strikethrough, autolinks via plugins"
```

### Task 2.3: render.py — wikilink preprocessor

**Files:**
- Modify: `src/md_viewer/render.py`
- Modify: `tests/test_render.py`

- [ ] **Step 1: Add failing tests**

Append to `tests/test_render.py`:
```python
def test_wikilink_basic():
    r = render_markdown("see [[Other]] for more")
    assert 'href="/api/file?path=/Other.md' in r["html"]
    assert ">Other</a>" in r["html"]


def test_wikilink_with_alias():
    r = render_markdown("see [[Other|display text]] here")
    assert ">display text</a>" in r["html"]
    assert 'href="/api/file?path=/Other.md' in r["html"]


def test_wikilink_explicit_md():
    r = render_markdown("see [[other.md]] here")
    assert 'href="/api/file?path=/other.md' in r["html"]


def test_wikilink_inside_paragraph():
    r = render_markdown("text [[Note]] more text")
    assert "<p>" in r["html"]
    assert "/api/file?path=/Note.md" in r["html"]
```

- [ ] **Step 2: Run to verify failure**

Run: `/media/data/venv/bin/pytest tests/test_render.py::test_wikilink_basic -v`
Expected: FAIL (no wikilink processing).

- [ ] **Step 3: Add preprocessor**

Append to `src/md_viewer/render.py`:
```python
import re as _re

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
```

Then in `render_markdown`, prepend a call to the preprocessor:
```python
def render_markdown(text: str) -> dict:
    text = _preprocess_wikilinks(text)
    tokens = _md.parse(text)
    html = _md.render(text)
    # ... rest unchanged
```

- [ ] **Step 4: Run to verify pass**

Run: `/media/data/venv/bin/pytest tests/test_render.py -v`
Expected: 16 passed.

- [ ] **Step 5: Commit**

```bash
git add src/md_viewer/render.py tests/test_render.py
git commit -m "feat(render): wikilink [[name]] and [[name|alias]] preprocessing"
```

---

