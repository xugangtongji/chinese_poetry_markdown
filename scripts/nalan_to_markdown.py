#!/usr/bin/env python3
"""Convert 纳兰性德/纳兰性德诗集.json → markdown/纳兰性德/.

258 records, all by 纳兰性德. Schema uses `para` (not `paragraphs`). Output
goes into one or more files: 纳兰性德_<count>.md (or _lo_hi.md if split).
"""
from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import sanitize, render_paragraphs, split_by_size, write_file, reset_dir

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "纳兰性德", "纳兰性德诗集.json")
OUT_DIR = os.path.join(ROOT, "纳兰性德")


def main() -> None:
    with open(SRC, encoding="utf-8") as f:
        records = json.load(f)

    intro = "# 纳兰性德\n\n"

    items = []
    total = skipped = 0
    for i, rec in enumerate(records, start=1):
        title = (rec.get("title") or "").strip()
        paras = [s for s in (rec.get("para") or []) if s and s.strip()]
        if not title or not paras:
            skipped += 1
            continue
        block = f"## {title}\n\n" + render_paragraphs(paras)
        items.append((i, block, len(block.encode("utf-8"))))
        total += 1

    reset_dir(OUT_DIR)
    if not items:
        print("纳兰性德: no records"); return

    parts = split_by_size(items, len(intro.encode("utf-8")), len(intro.encode("utf-8")))
    single = len(parts) == 1
    files_written = 0
    for part_num, (lo, hi, blks) in enumerate(parts, start=1):
        stem = f"纳兰性德_{hi}" if single else f"纳兰性德_{lo}_{hi}"
        write_file(os.path.join(OUT_DIR, stem + ".md"), intro + "".join(blks))
        files_written += 1

    print(f"纳兰性德: total={total}, skipped={skipped}, files={files_written}")


if __name__ == "__main__":
    main()
