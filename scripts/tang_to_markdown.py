#!/usr/bin/env python3
"""Convert 全唐诗/poet.tang.*.json → markdown/全唐诗/.

Multi-poem authors (>=2 poems) get their own ranked file(s):
    <rank>_<author>_<lo>_<hi>.md
where <rank> = author's position when sorted by descending poem count.
Poems within each author preserve original JSON source order.

Single-poem authors are merged into 千家诗_<lo>_<hi>.md files (size-split).
Each poem there is rendered as "## 题目（作者）".

Empty title → 无题. Empty body → skip.
"""
from __future__ import annotations

import glob
import json
import os
import re
import shutil
from collections import OrderedDict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_DIR = os.path.join(ROOT, "全唐诗")
OUT_DIR = os.path.join(ROOT, "markdown", "全唐诗")
SIZE_LIMIT = 200_000

UNSAFE = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


def sanitize(name: str) -> str:
    return UNSAFE.sub("_", name).strip() or "佚名"


def chunk_strides() -> list[int]:
    strides = []
    for p in glob.glob(os.path.join(SRC_DIR, "poet.tang.*.json")):
        m = re.search(r"poet\.tang\.(\d+)\.json$", p)
        if m:
            strides.append(int(m.group(1)))
    return sorted(strides)


def render_body(p: dict) -> str:
    paras = [s.strip() for s in (p.get("paragraphs") or []) if s and s.strip()]
    if not paras:
        return ""
    return "\n\n".join(paras) + "\n\n"


def poem_title(p: dict) -> str:
    return (p.get("title") or "").strip() or "无题"


def split_by_size(blocks_with_index, header_bytes_first, header_bytes_rest, limit):
    """Pack (one_based_index, block_string, block_bytes) items into parts.

    Returns list of (lo_index, hi_index, [block_strings]).
    """
    parts = []
    cur, cur_idx, cur_bytes = [], [], header_bytes_first
    for i, block, blen in blocks_with_index:
        if cur and cur_bytes + blen > limit:
            parts.append((cur_idx[0], cur_idx[-1], cur))
            cur, cur_idx, cur_bytes = [], [], header_bytes_rest
        cur.append(block)
        cur_idx.append(i)
        cur_bytes += blen
    if cur:
        parts.append((cur_idx[0], cur_idx[-1], cur))
    return parts


def main() -> None:
    with open(os.path.join(SRC_DIR, "authors.tang.json"), encoding="utf-8") as f:
        authors_desc = {r["name"]: (r.get("desc") or "").strip() for r in json.load(f)}

    by_author: "OrderedDict[str, list[dict]]" = OrderedDict()
    total = empty_body = empty_title = 0
    for stride in chunk_strides():
        with open(os.path.join(SRC_DIR, f"poet.tang.{stride}.json"), encoding="utf-8") as f:
            for poem in json.load(f):
                paras = [s for s in (poem.get("paragraphs") or []) if s and s.strip()]
                if not paras:
                    empty_body += 1
                    continue
                if not (poem.get("title") or "").strip():
                    empty_title += 1
                author = (poem.get("author") or "").strip() or "佚名"
                by_author.setdefault(author, []).append(poem)
                total += 1

    multi = [(a, ps) for a, ps in by_author.items() if len(ps) >= 2]
    singles = [(a, ps[0]) for a, ps in by_author.items() if len(ps) == 1]

    multi.sort(key=lambda kv: -len(kv[1]))
    rank_width = max(4, len(str(len(multi))))

    if os.path.isdir(OUT_DIR):
        shutil.rmtree(OUT_DIR)
    os.makedirs(OUT_DIR)

    files_written = 0
    used: set[str] = set()
    oversize: list[tuple[str, int]] = []

    for idx, (author, poems) in enumerate(multi, start=1):
        prefix = f"{idx:0{rank_width}d}"
        safe_author = sanitize(author)
        desc = authors_desc.get(author, "")
        intro = f"# {author}\n\n" + (desc + "\n\n" if desc else "")
        just_h1 = f"# {author}\n\n"

        blocks = []
        for i, poem in enumerate(poems, start=1):
            body = render_body(poem)
            if not body:
                continue
            block = f"## {poem_title(poem)}\n\n{body}"
            blocks.append((i, block, len(block.encode("utf-8"))))

        if not blocks:
            continue

        parts = split_by_size(
            blocks,
            header_bytes_first=len(intro.encode("utf-8")),
            header_bytes_rest=len(just_h1.encode("utf-8")),
            limit=SIZE_LIMIT,
        )

        for part_num, (lo, hi, blks) in enumerate(parts, start=1):
            header = intro if part_num == 1 else just_h1
            stem = f"{prefix}_{safe_author}_{lo}_{hi}"
            if stem in used:
                stem = f"{stem}-dup{part_num}"
            used.add(stem)
            content = header + "".join(blks)
            path = os.path.join(OUT_DIR, stem + ".md")
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(content)
            files_written += 1
            size = len(content.encode("utf-8"))
            if size > SIZE_LIMIT + 10_000:
                oversize.append((os.path.basename(path), size))

    qjs_h1 = "# 千家诗\n\n"
    qjs_blocks = []
    for i, (author, poem) in enumerate(singles, start=1):
        body = render_body(poem)
        if not body:
            continue
        block = f"## {poem_title(poem)}（{author}）\n\n{body}"
        qjs_blocks.append((i, block, len(block.encode("utf-8"))))

    if qjs_blocks:
        qjs_parts = split_by_size(
            qjs_blocks,
            header_bytes_first=len(qjs_h1.encode("utf-8")),
            header_bytes_rest=len(qjs_h1.encode("utf-8")),
            limit=SIZE_LIMIT,
        )
        for part_num, (lo, hi, blks) in enumerate(qjs_parts, start=1):
            stem = f"千家诗_{lo}_{hi}"
            content = qjs_h1 + "".join(blks)
            path = os.path.join(OUT_DIR, stem + ".md")
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(content)
            files_written += 1
            size = len(content.encode("utf-8"))
            if size > SIZE_LIMIT + 10_000:
                oversize.append((os.path.basename(path), size))

    print(f"authors total:        {len(by_author)}")
    print(f"  multi-poem authors: {len(multi)}")
    print(f"  single-poem authors:{len(singles)}")
    print(f"poems rendered:       {total}")
    print(f"empty titles→无题:    {empty_title}")
    print(f"skipped empty body:   {empty_body}")
    print(f"files written:        {files_written}")
    if oversize:
        print(f"oversize files:       {len(oversize)}")
        for n, s in oversize[:10]:
            print(f"  {n}: {s}")


if __name__ == "__main__":
    main()
