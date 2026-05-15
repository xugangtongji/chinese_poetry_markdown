#!/usr/bin/env python3
"""Convert 元曲/yuanqu.json → markdown/元曲/.

Records: {title, author, paragraphs, dynasty}. Same per-author layout as tang.
Single-piece authors → 千家曲_*.md as "## 题目（作者）".
"""
from __future__ import annotations

import json
import os
import sys
from collections import OrderedDict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import sanitize, render_paragraphs, split_by_size, write_file, reset_dir

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "元曲", "yuanqu.json")
OUT_DIR = os.path.join(ROOT, "元曲")


def main() -> None:
    with open(SRC, encoding="utf-8") as f:
        records = json.load(f)

    by_author: "OrderedDict[str, list[dict]]" = OrderedDict()
    total = skipped = 0
    for rec in records:
        title = (rec.get("title") or "").strip()
        paras = [s for s in (rec.get("paragraphs") or []) if s and s.strip()]
        if not title or not paras:
            skipped += 1
            continue
        author = (rec.get("author") or "").strip() or "佚名"
        by_author.setdefault(author, []).append(rec)
        total += 1

    multi = [(a, ps) for a, ps in by_author.items() if len(ps) >= 2]
    singles = [(a, ps[0]) for a, ps in by_author.items() if len(ps) == 1]
    multi.sort(key=lambda kv: -len(kv[1]))
    width = max(4, len(str(len(multi))))

    reset_dir(OUT_DIR)
    files_written = 0
    used: set[str] = set()

    for idx, (author, recs) in enumerate(multi, start=1):
        prefix = f"{idx:0{width}d}"
        safe_author = sanitize(author)
        intro = f"# {author}\n\n"

        items = []
        for i, rec in enumerate(recs, start=1):
            title = rec["title"].strip()
            body = render_paragraphs(rec.get("paragraphs") or [])
            if not body:
                continue
            block = f"## {title}\n\n{body}"
            items.append((i, block, len(block.encode("utf-8"))))

        if not items:
            continue

        parts = split_by_size(items, len(intro.encode("utf-8")), len(intro.encode("utf-8")))
        single_part = len(parts) == 1
        for part_num, (lo, hi, blks) in enumerate(parts, start=1):
            stem = f"{prefix}_{safe_author}_{hi}" if single_part else f"{prefix}_{safe_author}_{lo}_{hi}"
            if stem in used:
                stem = f"{stem}-dup{part_num}"
            used.add(stem)
            write_file(os.path.join(OUT_DIR, stem + ".md"), intro + "".join(blks))
            files_written += 1

    qjs_h1 = "# 千家曲\n\n"
    items = []
    for i, (author, rec) in enumerate(singles, start=1):
        title = rec["title"].strip()
        body = render_paragraphs(rec.get("paragraphs") or [])
        if not body:
            continue
        block = f"## {title}（{author}）\n\n{body}"
        items.append((i, block, len(block.encode("utf-8"))))
    if items:
        parts = split_by_size(items, len(qjs_h1.encode("utf-8")), len(qjs_h1.encode("utf-8")))
        single = len(parts) == 1
        for part_num, (lo, hi, blks) in enumerate(parts, start=1):
            stem = f"千家曲_{hi}" if single else f"千家曲_{lo}_{hi}"
            write_file(os.path.join(OUT_DIR, stem + ".md"), qjs_h1 + "".join(blks))
            files_written += 1

    print(f"元曲: total={total}, skipped={skipped}, authors={len(by_author)}, "
          f"multi={len(multi)}, single={len(singles)}, files={files_written}")


if __name__ == "__main__":
    main()
