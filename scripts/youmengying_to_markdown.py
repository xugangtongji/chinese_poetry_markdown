#!/usr/bin/env python3
"""Convert 幽梦影/youmengying.json → markdown/幽梦影/.

219 aphorisms, each {content (string), comment (list of strings)}.
Single output file 幽梦影.md, with each aphorism as "## 其N" followed by
content and any comments rendered as blockquotes.
"""
from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import split_by_size, write_file, reset_dir

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "幽梦影", "youmengying.json")
OUT_DIR = os.path.join(ROOT, "markdown", "幽梦影")

CN_NUM = "零一二三四五六七八九"


def cn_number(n: int) -> str:
    if n < 10:
        return CN_NUM[n]
    if n < 100:
        tens, ones = divmod(n, 10)
        s = (CN_NUM[tens] if tens != 1 else "") + "十"
        if ones:
            s += CN_NUM[ones]
        return s
    hundreds, rest = divmod(n, 100)
    s = CN_NUM[hundreds] + "百"
    if rest:
        if rest < 10:
            s += "零" + CN_NUM[rest]
        else:
            tens, ones = divmod(rest, 10)
            s += (CN_NUM[tens] if tens else "零") + ("十" if tens else "")
            if ones:
                s += CN_NUM[ones]
    return s


def main() -> None:
    with open(SRC, encoding="utf-8") as f:
        records = json.load(f)

    h1 = "# 幽梦影\n\n张潮\n\n"
    items = []
    for i, rec in enumerate(records, start=1):
        content = (rec.get("content") or "").strip()
        if not content:
            continue
        head = f"## 其{cn_number(i)}"
        comments = [c.strip() for c in (rec.get("comment") or []) if c and c.strip()]
        body = content + "\n\n"
        if comments:
            body += "\n".join(f"> {c}" for c in comments) + "\n\n"
        block = f"{head}\n\n{body}"
        items.append((i, block, len(block.encode("utf-8"))))

    reset_dir(OUT_DIR)
    parts = split_by_size(items, len(h1.encode("utf-8")), len(h1.encode("utf-8")))
    single = len(parts) == 1
    files_written = 0
    for part_num, (lo, hi, blks) in enumerate(parts, start=1):
        stem = "幽梦影" if single else f"幽梦影_{lo}_{hi}"
        write_file(os.path.join(OUT_DIR, stem + ".md"), h1 + "".join(blks))
        files_written += 1
    print(f"幽梦影: total={len(items)}, files={files_written}")


if __name__ == "__main__":
    main()
