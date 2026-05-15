"""Shared helpers for corpus → markdown converters."""
from __future__ import annotations

import os
import re

UNSAFE = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
SIZE_LIMIT = 200_000

_t2s = None


def to_simplified(text: str) -> str:
    """Convert traditional Chinese text to simplified via opencc.
    Lazily initialized; returns input unchanged if opencc is unavailable."""
    global _t2s
    if _t2s is None:
        try:
            from opencc import OpenCC
            _t2s = OpenCC("t2s")
        except ImportError:
            _t2s = False
    if _t2s is False:
        return text
    return _t2s.convert(text)


def sanitize(name: str, fallback: str = "_") -> str:
    out = UNSAFE.sub("_", name).strip()
    return out or fallback


def truncate_for_filename(s: str, max_chars: int = 60) -> str:
    return s if len(s) <= max_chars else s[:max_chars] + "…"


def render_paragraphs(paras: list[str]) -> str:
    """Render a list of paragraph strings as markdown blocks (blank-line separated)."""
    cleaned = [p.strip() for p in paras if p and p.strip()]
    if not cleaned:
        return ""
    return "\n\n".join(cleaned) + "\n\n"


def split_by_size(
    items: list[tuple[int, str, int]],
    header_bytes_first: int,
    header_bytes_rest: int,
    limit: int = SIZE_LIMIT,
) -> list[tuple[int, int, list[str]]]:
    """items: list of (one-based index, block string, block bytes).
    Returns list of (lo_index, hi_index, [block strings]).
    """
    parts: list[tuple[int, int, list[str]]] = []
    cur: list[str] = []
    cur_idx: list[int] = []
    cur_bytes = header_bytes_first
    for i, block, blen in items:
        if cur and cur_bytes + blen > limit:
            parts.append((cur_idx[0], cur_idx[-1], cur))
            cur, cur_idx = [], []
            cur_bytes = header_bytes_rest
        cur.append(block)
        cur_idx.append(i)
        cur_bytes += blen
    if cur:
        parts.append((cur_idx[0], cur_idx[-1], cur))
    return parts


def write_file(path: str, content: str) -> int:
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return len(content.encode("utf-8"))


def reset_dir(path: str) -> None:
    """Ensure path exists and remove only *.md files inside it.

    The corpus directories at the repo root hold both source JSON and
    generated .md files alongside each other; we must not wipe everything.
    """
    os.makedirs(path, exist_ok=True)
    for f in os.listdir(path):
        full = os.path.join(path, f)
        if os.path.isfile(full) and f.endswith(".md"):
            os.remove(full)
