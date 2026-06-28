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

    CONTENT_EXTS: frozenset[str] = frozenset({".md", ".markdown", ".mdx"})
    IMAGE_EXTS: frozenset[str] = frozenset(
        {".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg"}
    )

    @property
    def content_exts(self) -> frozenset[str]:
        return self.CONTENT_EXTS

    @property
    def image_exts(self) -> frozenset[str]:
        return self.IMAGE_EXTS

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
