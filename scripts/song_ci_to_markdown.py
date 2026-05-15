#!/usr/bin/env python3
"""Convert 宋词/ci.song.*.json → markdown/宋词/.

Records: {author, paragraphs, rhythmic}.  rhythmic (词牌名) is used as the
H2 title (no separate title field exists). Authors with ≥2 ci get their
own file(s); single-ci authors are merged into 千家词_*.md as
"## 词牌（作者）".
"""
from __future__ import annotations

import glob
import json
import os
import re
import sys
from collections import OrderedDict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import sanitize, render_paragraphs, split_by_size, write_file, reset_dir, SIZE_LIMIT

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_DIR = os.path.join(ROOT, "宋词")
OUT_DIR = os.path.join(ROOT, "markdown", "宋词")


PLACEHOLDER_DESC = re.compile(r"^[\s\-—–_]*$")


def load_authors() -> dict[str, str]:
    with open(os.path.join(SRC_DIR, "author.song.json"), encoding="utf-8") as f:
        out = {}
        for r in json.load(f):
            desc = (r.get("description") or "").strip()
            if PLACEHOLDER_DESC.match(desc):
                desc = ""
            out[r["name"]] = desc
        return out


def chunk_strides() -> list[int]:
    strides = []
    for p in glob.glob(os.path.join(SRC_DIR, "ci.song.*.json")):
        m = re.search(r"ci\.song\.(\d+)\.json$", p)
        if m:
            strides.append(int(m.group(1)))
    return sorted(strides)


def main() -> None:
    authors_desc = load_authors()
    by_author: "OrderedDict[str, list[dict]]" = OrderedDict()
    total = skipped = 0
    for stride in chunk_strides():
        with open(os.path.join(SRC_DIR, f"ci.song.{stride}.json"), encoding="utf-8") as f:
            for rec in json.load(f):
                paras = [s for s in (rec.get("paragraphs") or []) if s and s.strip()]
                rhythmic = (rec.get("rhythmic") or "").strip()
                if not paras or not rhythmic:
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
        desc = authors_desc.get(author, "")
        intro = f"# {author}\n\n" + (desc + "\n\n" if desc else "")
        just_h1 = f"# {author}\n\n"

        items = []
        for i, rec in enumerate(recs, start=1):
            rhythmic = rec["rhythmic"].strip()
            body = render_paragraphs(rec.get("paragraphs") or [])
            if not body:
                continue
            block = f"## {rhythmic}\n\n{body}"
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
            content = header + "".join(blks)
            write_file(os.path.join(OUT_DIR, stem + ".md"), content)
            files_written += 1

    # 千家词 bucket
    qjs_h1 = "# 千家词\n\n"
    items = []
    for i, (author, rec) in enumerate(singles, start=1):
        rhythmic = rec["rhythmic"].strip()
        body = render_paragraphs(rec.get("paragraphs") or [])
        if not body:
            continue
        block = f"## {rhythmic}（{author}）\n\n{body}"
        items.append((i, block, len(block.encode("utf-8"))))
    if items:
        parts = split_by_size(items, len(qjs_h1.encode("utf-8")), len(qjs_h1.encode("utf-8")))
        single = len(parts) == 1
        for part_num, (lo, hi, blks) in enumerate(parts, start=1):
            stem = f"千家词_{hi}" if single else f"千家词_{lo}_{hi}"
            content = qjs_h1 + "".join(blks)
            write_file(os.path.join(OUT_DIR, stem + ".md"), content)
            files_written += 1

    print(f"宋词: total={total}, skipped={skipped}, authors={len(by_author)}, "
          f"multi={len(multi)}, single={len(singles)}, files={files_written}")


if __name__ == "__main__":
    main()
