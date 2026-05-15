#!/usr/bin/env python3
"""Convert 曹操诗集/caocao.json → markdown/曹操诗集/.

26 records, all by 曹操 (the source records have no `author` field, but
the corpus is dedicated to him). Single output file: 曹操_<count>.md.
"""
from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import render_paragraphs, split_by_size, write_file, reset_dir

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "曹操诗集", "caocao.json")
OUT_DIR = os.path.join(ROOT, "曹操诗集")


def main() -> None:
    with open(SRC, encoding="utf-8") as f:
        records = json.load(f)

    intro = "# 曹操\n\n"
    items = []
    total = skipped = 0
    for i, rec in enumerate(records, start=1):
        title = (rec.get("title") or "").strip()
        paras = [s for s in (rec.get("paragraphs") or []) if s and s.strip()]
        if not title or not paras:
            skipped += 1
            continue
        block = f"## {title}\n\n" + render_paragraphs(paras)
        items.append((i, block, len(block.encode("utf-8"))))
        total += 1

    reset_dir(OUT_DIR)
    parts = split_by_size(items, len(intro.encode("utf-8")), len(intro.encode("utf-8")))
    single = len(parts) == 1
    files_written = 0
    for part_num, (lo, hi, blks) in enumerate(parts, start=1):
        stem = f"曹操_{hi}" if single else f"曹操_{lo}_{hi}"
        write_file(os.path.join(OUT_DIR, stem + ".md"), intro + "".join(blks))
        files_written += 1

    print(f"曹操诗集: total={total}, skipped={skipped}, files={files_written}")


if __name__ == "__main__":
    main()
