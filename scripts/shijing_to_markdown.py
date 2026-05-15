#!/usr/bin/env python3
"""Convert 诗经/shijing.json → markdown/诗经/.

305 records: {title, chapter, section, content}. chapter ∈ {国风, 小雅,
大雅, 颂}. Output one file per chapter, with H2 = "<section> <title>"
within (subsections like 周南/召南 under 国风, 周颂/鲁颂/商颂 under 颂).
"""
from __future__ import annotations

import json
import os
import sys
from collections import OrderedDict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import sanitize, render_paragraphs, split_by_size, write_file, reset_dir

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "诗经", "shijing.json")
OUT_DIR = os.path.join(ROOT, "markdown", "诗经")


def main() -> None:
    with open(SRC, encoding="utf-8") as f:
        records = json.load(f)

    by_chapter: "OrderedDict[str, list[dict]]" = OrderedDict()
    total = skipped = 0
    for rec in records:
        content = [s for s in (rec.get("content") or []) if s and s.strip()]
        title = (rec.get("title") or "").strip()
        chapter = (rec.get("chapter") or "其他").strip()
        if not content or not title:
            skipped += 1
            continue
        by_chapter.setdefault(chapter, []).append(rec)
        total += 1

    reset_dir(OUT_DIR)
    files_written = 0
    for chapter, recs in by_chapter.items():
        safe = sanitize(chapter)
        h1 = f"# {chapter}\n\n"
        items = []
        for i, rec in enumerate(recs, start=1):
            title = rec["title"].strip()
            section = (rec.get("section") or "").strip()
            head = f"## {section}·{title}" if section else f"## {title}"
            body = render_paragraphs(rec.get("content") or [])
            block = f"{head}\n\n{body}"
            items.append((i, block, len(block.encode("utf-8"))))
        if not items:
            continue
        parts = split_by_size(items, len(h1.encode("utf-8")), len(h1.encode("utf-8")))
        single = len(parts) == 1
        for part_num, (lo, hi, blks) in enumerate(parts, start=1):
            suffix = "" if single else f"_{lo}_{hi}"
            stem = f"{safe}{suffix}"
            write_file(os.path.join(OUT_DIR, stem + ".md"), h1 + "".join(blks))
            files_written += 1

    print(f"诗经: total={total}, skipped={skipped}, chapters={len(by_chapter)}, files={files_written}")


if __name__ == "__main__":
    main()
