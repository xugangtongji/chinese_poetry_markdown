#!/usr/bin/env python3
"""Convert 四书五经/{daxue,zhongyong,mengzi}.json → markdown/四书五经/.

- daxue.json: dict {chapter, paragraphs}     → 大学.md
- zhongyong.json: dict {chapter, paragraphs} → 中庸.md
- mengzi.json: list of {chapter, paragraphs} → 孟子.md (one H2 per chapter)
"""
from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import render_paragraphs, split_by_size, write_file, reset_dir, to_simplified

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_DIR = os.path.join(ROOT, "四书五经")
OUT_DIR = os.path.join(ROOT, "markdown", "四书五经")

NAMES = {"daxue": "大学", "zhongyong": "中庸", "mengzi": "孟子"}


def main() -> None:
    reset_dir(OUT_DIR)
    files_written = 0

    for fname, label in NAMES.items():
        path = os.path.join(SRC_DIR, f"{fname}.json")
        if not os.path.isfile(path):
            continue
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        h1 = f"# {label}\n\n"
        items = []
        if isinstance(data, dict):
            paras = [s for s in (data.get("paragraphs") or []) if s and s.strip()]
            chapter = (data.get("chapter") or label).strip()
            if paras:
                block = f"## {chapter}\n\n" + render_paragraphs(paras)
                items.append((1, block, len(block.encode("utf-8"))))
        else:
            for i, rec in enumerate(data, start=1):
                chapter = (rec.get("chapter") or "").strip()
                paras = [s for s in (rec.get("paragraphs") or []) if s and s.strip()]
                if not chapter or not paras:
                    continue
                block = f"## {chapter}\n\n" + render_paragraphs(paras)
                items.append((i, block, len(block.encode("utf-8"))))
        if not items:
            continue
        parts = split_by_size(items, len(h1.encode("utf-8")), len(h1.encode("utf-8")))
        single = len(parts) == 1
        for part_num, (lo, hi, blks) in enumerate(parts, start=1):
            stem = label if single else f"{label}_{lo}_{hi}"
            write_file(os.path.join(OUT_DIR, stem + ".md"), to_simplified(h1 + "".join(blks)))
            files_written += 1
    print(f"四书五经: files={files_written}")


if __name__ == "__main__":
    main()
