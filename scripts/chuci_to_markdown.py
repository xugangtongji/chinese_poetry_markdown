#!/usr/bin/env python3
"""Convert 楚辞/chuci.json → markdown/楚辞/.

65 records: {author, title, section, content}. Output one file per section
(离骚, 九歌, 九章, 天问, ...), each containing the records under that
section in source order. H2 = title; author shown inline when not 屈原.
"""
from __future__ import annotations

import json
import os
import sys
from collections import OrderedDict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import sanitize, render_paragraphs, split_by_size, write_file, reset_dir

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "楚辞", "chuci.json")
OUT_DIR = os.path.join(ROOT, "markdown", "楚辞")


def main() -> None:
    with open(SRC, encoding="utf-8") as f:
        records = json.load(f)

    by_section: "OrderedDict[str, list[dict]]" = OrderedDict()
    total = skipped = 0
    for rec in records:
        content = [s for s in (rec.get("content") or []) if s and s.strip()]
        title = (rec.get("title") or "").strip()
        section = (rec.get("section") or "其他").strip()
        if not content or not title:
            skipped += 1
            continue
        by_section.setdefault(section, []).append(rec)
        total += 1

    reset_dir(OUT_DIR)
    files_written = 0
    for section, recs in by_section.items():
        safe = sanitize(section)
        h1 = f"# {section}\n\n"
        items = []
        for i, rec in enumerate(recs, start=1):
            title = rec["title"].strip()
            author = (rec.get("author") or "").strip()
            head = f"## {title}（{author}）" if author and author != "屈原" else f"## {title}"
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

    print(f"楚辞: total={total}, skipped={skipped}, sections={len(by_section)}, files={files_written}")


if __name__ == "__main__":
    main()
