#!/usr/bin/env python3
"""Convert 论语/lunyu.json → markdown/论语/.

20 records: {chapter, paragraphs}. Output a single 论语.md with each chapter
as an H2 section.
"""
from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import render_paragraphs, split_by_size, write_file, reset_dir

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "论语", "lunyu.json")
OUT_DIR = os.path.join(ROOT, "markdown", "论语")


def main() -> None:
    with open(SRC, encoding="utf-8") as f:
        records = json.load(f)

    h1 = "# 论语\n\n"
    items = []
    for i, rec in enumerate(records, start=1):
        chapter = (rec.get("chapter") or "").strip()
        paras = [s for s in (rec.get("paragraphs") or []) if s and s.strip()]
        if not chapter or not paras:
            continue
        block = f"## {chapter}\n\n" + render_paragraphs(paras)
        items.append((i, block, len(block.encode("utf-8"))))

    reset_dir(OUT_DIR)
    parts = split_by_size(items, len(h1.encode("utf-8")), len(h1.encode("utf-8")))
    single = len(parts) == 1
    files_written = 0
    for part_num, (lo, hi, blks) in enumerate(parts, start=1):
        stem = "论语" if single else f"论语_{lo}_{hi}"
        write_file(os.path.join(OUT_DIR, stem + ".md"), h1 + "".join(blks))
        files_written += 1
    print(f"论语: chapters={len(items)}, files={files_written}")


if __name__ == "__main__":
    main()
