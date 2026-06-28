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
