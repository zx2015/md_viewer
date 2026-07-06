"""Runtime configuration loaded from environment variables."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class Config:
    root: Path = Path("/data")
    host: str = "0.0.0.0"
    port: int = 8000
    max_file_size: int = 5 * 1024 * 1024

    content_exts: frozenset[str] = frozenset({
        ".md", ".markdown", ".mdx",
        ".py", ".json", ".html", ".htm",
    })
    image_exts: frozenset[str] = frozenset(
        {".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg"}
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
