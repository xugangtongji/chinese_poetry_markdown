#!/usr/bin/env python3
"""Convert 全唐诗/poet.tang.*.json → markdown/全唐诗/作者_N.md."""
from __future__ import annotations

import glob
import json
import os
import re
from collections import OrderedDict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_DIR = os.path.join(ROOT, "全唐诗")
OUT_DIR = os.path.join(ROOT, "markdown", "全唐诗")
SIZE_LIMIT = 200_000  # bytes (UTF-8)

UNSAFE = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


def sanitize(name: str) -> str:
    name = UNSAFE.sub("_", name).strip()
    return name or "佚名"


def load_authors() -> dict[str, str]:
    with open(os.path.join(SRC_DIR, "authors.tang.json"), encoding="utf-8") as f:
        return {r["name"]: (r.get("desc") or "").strip() for r in json.load(f)}


def iter_tang_chunks():
    paths = glob.glob(os.path.join(SRC_DIR, "poet.tang.*.json"))
    paths.sort(key=lambda p: int(re.search(r"poet\.tang\.(\d+)\.json$", p).group(1)))
    for p in paths:
        with open(p, encoding="utf-8") as f:
            yield from json.load(f)


def render_poem(p: dict) -> str:
    title = (p.get("title") or "").strip()
    paras = [s.strip() for s in (p.get("paragraphs") or []) if s and s.strip()]
    if not title or not paras:
        return ""
    return f"## {title}\n\n" + "\n\n".join(paras) + "\n\n"


def main() -> None:
    os.makedirs(OUT_DIR, exist_ok=True)
    authors = load_authors()

    by_author: "OrderedDict[str, list[dict]]" = OrderedDict()
    total_poems = 0
    skipped = 0
    for poem in iter_tang_chunks():
        author = (poem.get("author") or "").strip() or "佚名"
        block = render_poem(poem)
        if not block:
            skipped += 1
            continue
        by_author.setdefault(author, []).append((block, len(block.encode("utf-8"))))
        total_poems += 1

    used_filenames: set[str] = set()
    files_written = 0
    oversize_files: list[tuple[str, int]] = []
    sanitize_collisions: list[tuple[str, str]] = []
    authors_without_desc = 0

    for author, blocks in by_author.items():
        base = sanitize(author)
        if base in used_filenames:
            disambig = f"{base}-{abs(hash(author)) % 100000:05d}"
            sanitize_collisions.append((author, disambig))
            base = disambig
        used_filenames.add(base)

        desc = authors.get(author, "")
        if not desc:
            authors_without_desc += 1

        intro = f"# {author}\n\n"
        if desc:
            intro += desc + "\n\n"
        just_h1 = f"# {author}\n\n"

        parts: list[list[str]] = []
        current: list[str] = []
        current_bytes = len(intro.encode("utf-8"))
        for block, block_bytes in blocks:
            if current and current_bytes + block_bytes > SIZE_LIMIT:
                parts.append(current)
                current = []
                current_bytes = len(just_h1.encode("utf-8"))
            current.append(block)
            current_bytes += block_bytes
        if current:
            parts.append(current)

        for i, part_blocks in enumerate(parts, start=1):
            header = intro if i == 1 else just_h1
            content = header + "".join(part_blocks)
            path = os.path.join(OUT_DIR, f"{base}_{i}.md")
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
            files_written += 1
            size = len(content.encode("utf-8"))
            if size > SIZE_LIMIT + 10_000:  # tolerance for final poem in part
                oversize_files.append((os.path.basename(path), size))

    print(f"authors:           {len(by_author)}")
    print(f"poems rendered:    {total_poems}")
    print(f"poems skipped:     {skipped} (empty title or body)")
    print(f"files written:     {files_written}")
    print(f"authors w/o desc:  {authors_without_desc}")
    if sanitize_collisions:
        print(f"name collisions:   {len(sanitize_collisions)}")
        for a, b in sanitize_collisions[:10]:
            print(f"  {a!r} -> {b}")
    if oversize_files:
        print(f"oversize files:    {len(oversize_files)} (> {SIZE_LIMIT + 10_000} bytes)")
        for name, size in oversize_files[:10]:
            print(f"  {name}: {size} bytes")


if __name__ == "__main__":
    main()
