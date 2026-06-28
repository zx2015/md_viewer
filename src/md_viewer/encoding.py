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
