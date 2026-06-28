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


def _build_node(path: Path, name: str, root: Path, content_exts: frozenset[str]) -> TreeNode:
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
        if entry.is_dir():
            children.append(_build_node(entry, entry.name, cfg.root, cfg.content_exts))
        elif entry.suffix.lower() in cfg.content_exts:
            children.append(_build_node(entry, entry.name, cfg.root, cfg.content_exts))
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
