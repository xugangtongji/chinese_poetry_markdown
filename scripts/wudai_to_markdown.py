#!/usr/bin/env python3
"""Convert 五代诗词/{huajianji,nantang} → markdown/五代诗词/.

Combines 花间集 (10 files) + 南唐 (1 file + authors.json) into one
per-author layout. Records: {author, title, rhythmic, paragraphs, notes}.
H2 line shows both title and 词牌名 when both present. Single-piece authors
→ 千家集_*.md as "## 标题（作者）".
"""
from __future__ import annotations

import glob
import json
import os
import sys
from collections import OrderedDict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import sanitize, render_paragraphs, split_by_size, write_file, reset_dir

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HJJ_DIR = os.path.join(ROOT, "五代诗词", "huajianji")
NT_DIR = os.path.join(ROOT, "五代诗词", "nantang")
OUT_DIR = os.path.join(ROOT, "markdown", "五代诗词")


def heading_for(rec: dict) -> str:
    title = (rec.get("title") or "").strip()
    rhythmic = (rec.get("rhythmic") or "").strip()
    if title and rhythmic and rhythmic not in title:
        return f"{rhythmic} {title}"
    return title or rhythmic


def main() -> None:
    nt_authors: dict[str, str] = {}
    try:
        with open(os.path.join(NT_DIR, "authors.json"), encoding="utf-8") as f:
            nt_authors = {r["name"]: (r.get("desc") or "").strip() for r in json.load(f)}
    except FileNotFoundError:
        pass

    by_author: "OrderedDict[str, list[dict]]" = OrderedDict()
    total = skipped = 0

    # 花间集 — chunked
    for path in sorted(glob.glob(os.path.join(HJJ_DIR, "huajianji-*.json"))):
        with open(path, encoding="utf-8") as f:
            for rec in json.load(f):
                paras = [s for s in (rec.get("paragraphs") or []) if s and s.strip()]
                head = heading_for(rec)
                if not paras or not head:
                    skipped += 1
                    continue
                author = (rec.get("author") or "").strip() or "佚名"
                by_author.setdefault(author, []).append(rec)
                total += 1

    # 南唐 — single file
    nt_path = os.path.join(NT_DIR, "poetrys.json")
    if os.path.isfile(nt_path):
        with open(nt_path, encoding="utf-8") as f:
            for rec in json.load(f):
                paras = [s for s in (rec.get("paragraphs") or []) if s and s.strip()]
                head = heading_for(rec)
                if not paras or not head:
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
        desc = nt_authors.get(author, "")
        intro = f"# {author}\n\n" + (desc + "\n\n" if desc else "")
        just_h1 = f"# {author}\n\n"

        items = []
        for i, rec in enumerate(recs, start=1):
            body = render_paragraphs(rec.get("paragraphs") or [])
            head = heading_for(rec)
            if not body:
                continue
            block = f"## {head}\n\n{body}"
            items.append((i, block, len(block.encode("utf-8"))))

        if not items:
            continue

        parts = split_by_size(items, len(intro.encode("utf-8")), len(just_h1.encode("utf-8")))
        single_part = len(parts) == 1
        for part_num, (lo, hi, blks) in enumerate(parts, start=1):
            header = intro if part_num == 1 else just_h1
            stem = f"{prefix}_{safe_author}_{hi}" if single_part else f"{prefix}_{safe_author}_{lo}_{hi}"
            if stem in used:
                stem = f"{stem}-dup{part_num}"
            used.add(stem)
            write_file(os.path.join(OUT_DIR, stem + ".md"), header + "".join(blks))
            files_written += 1

    qjs_h1 = "# 千家集\n\n"
    items = []
    for i, (author, rec) in enumerate(singles, start=1):
        body = render_paragraphs(rec.get("paragraphs") or [])
        head = heading_for(rec)
        if not body:
            continue
        block = f"## {head}（{author}）\n\n{body}"
        items.append((i, block, len(block.encode("utf-8"))))
    if items:
        parts = split_by_size(items, len(qjs_h1.encode("utf-8")), len(qjs_h1.encode("utf-8")))
        single = len(parts) == 1
        for part_num, (lo, hi, blks) in enumerate(parts, start=1):
            stem = f"千家集_{hi}" if single else f"千家集_{lo}_{hi}"
            write_file(os.path.join(OUT_DIR, stem + ".md"), qjs_h1 + "".join(blks))
            files_written += 1

    print(f"五代诗词: total={total}, skipped={skipped}, authors={len(by_author)}, "
          f"multi={len(multi)}, single={len(singles)}, files={files_written}")


if __name__ == "__main__":
    main()
