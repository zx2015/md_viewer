"""Path and extension validation. Defense against ../ escape and bad inputs."""
from __future__ import annotations

from pathlib import Path


class PathError(ValueError):
    """Raised when a path resolves outside the allowed root."""


class ExtensionError(ValueError):
    """Raised when a file extension is not in the whitelist."""


def resolve_safe(path_str: str, root: Path) -> Path:
    """Resolve a user-provided path against ``root``.

    All paths are treated as paths-within-root: a leading ``/`` is stripped
    so that API paths like ``/docs/a.md`` map to ``<root>/docs/a.md``.
    This is appropriate for an app that always operates within a single
    root directory.

    Raises ``PathError`` if the resolved path escapes ``root``.
    """
    if not path_str:
        raise PathError("Empty path")
    # Strip leading slashes — treat the entire input as path-within-root
    rel = path_str.lstrip("/")
    p = (root / rel).resolve()
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
