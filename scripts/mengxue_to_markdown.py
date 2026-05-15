#!/usr/bin/env python3
"""Convert 蒙学/*.json → markdown/蒙学/.

Each book gets a single output file named after its `title`. Books have
heterogeneous shapes:
- flat: {title, paragraphs}                          (e.g. 百家姓, 千字文, 三字经, 朱子家训)
- chapters: {title, content: [{chapter, paragraphs}]} (e.g. 弟子规, 增广贤文)
- juans:    {title, content: [{title, paragraphs}]}   (e.g. 文字蒙求)
- nested:   {title, content: [{title, content: [{chapter, paragraphs}]}]}  (e.g. 幼学琼林)
- with author: {title, content: [{type/title, content: [{chapter, author, paragraphs}]}]}
                                                     (e.g. 千家诗, 唐诗三百首, 古文观止)

A recursive renderer handles all of these uniformly.
"""
from __future__ import annotations

import glob
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import sanitize, split_by_size, write_file, reset_dir, SIZE_LIMIT, to_simplified

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_DIR = os.path.join(ROOT, "蒙学")
OUT_DIR = os.path.join(ROOT, "markdown", "蒙学")


def render_node(node, depth: int) -> str:
    if isinstance(node, list):
        return "".join(render_node(c, depth) for c in node)
    if not isinstance(node, dict):
        s = str(node).strip()
        return s + "\n\n" if s else ""

    heading = node.get("chapter") or node.get("title") or node.get("type")
    subchapter = node.get("subchapter")
    if heading and subchapter and not node.get("paragraphs"):
        heading = f"{heading}·{subchapter}"
    elif not heading and subchapter:
        heading = subchapter
    author = (node.get("author") or "").strip()
    raw_paras = node.get("paragraphs") or []
    # paragraphs may mix strings and dicts (e.g. qianjiashi sub-poems)
    str_paras = [p.strip() for p in raw_paras if isinstance(p, str) and p.strip()]
    dict_paras = [p for p in raw_paras if isinstance(p, dict)]
    inner = node.get("content")

    out = ""
    if heading:
        level = min(max(depth, 1), 6)
        head_text = heading.strip()
        if author and (str_paras or dict_paras):
            head_text += f"（{author}）"
        out += ("#" * level) + " " + head_text + "\n\n"
    if str_paras:
        out += "\n\n".join(str_paras) + "\n\n"
    if dict_paras:
        next_depth = depth + 1 if heading else depth
        out += render_node(dict_paras, next_depth)
    if inner is not None:
        next_depth = depth + 1 if heading else depth
        out += render_node(inner, next_depth)
    return out


def main() -> None:
    reset_dir(OUT_DIR)
    total_files = 0
    used_stems: set[str] = set()
    for path in sorted(glob.glob(os.path.join(SRC_DIR, "*.json"))):
        with open(path, encoding="utf-8") as f:
            book = json.load(f)
        if not isinstance(book, dict):
            continue
        title = (book.get("title") or os.path.basename(path)).strip()
        author = (book.get("author") or "").strip()
        abstract = (book.get("abstract") or "").strip() if isinstance(book.get("abstract"), str) else ""
        if not abstract and isinstance(book.get("abstract"), list):
            abstract = "\n\n".join(s.strip() for s in book["abstract"] if s and s.strip())
        preface = book.get("preface")
        preface_text = ""
        if isinstance(preface, str):
            preface_text = preface.strip()
        elif isinstance(preface, list):
            preface_text = "\n\n".join(s.strip() for s in preface if s and s.strip())

        h1 = f"# {title}\n\n"
        if author:
            h1 += f"作者：{author}\n\n"
        if abstract:
            h1 += abstract + "\n\n"
        if preface_text:
            h1 += "## 序\n\n" + preface_text + "\n\n"

        body = ""
        top_paras = [p.strip() for p in (book.get("paragraphs") or []) if p and p.strip()]
        if top_paras:
            body += "\n\n".join(top_paras) + "\n\n"
        if book.get("content"):
            body += render_node(book["content"], depth=2)

        safe = sanitize(to_simplified(title))
        # disambiguate if multiple source files share title (e.g. sanzijing-new vs sanzijing-traditional)
        tags = (book.get("tags") or "").strip()
        if safe in used_stems and tags:
            safe = f"{safe}_{sanitize(to_simplified(tags))}"
        if safe in used_stems:
            safe = f"{safe}_{os.path.splitext(os.path.basename(path))[0]}"
        used_stems.add(safe)
        # split by size while keeping H1 intact in part 1 and using just-H1 in continuations
        # body is already a single string; pack by section breaks ("\n## " boundaries)
        full = h1 + body
        if len(full.encode("utf-8")) <= SIZE_LIMIT + 10_000:
            write_file(os.path.join(OUT_DIR, safe + ".md"), to_simplified(full))
            total_files += 1
        else:
            # Split body at H2 boundaries
            sections = body.split("\n## ")
            sections = [sections[0]] + ["## " + s for s in sections[1:]]
            # pack
            cur, cur_bytes, parts = [], len(h1.encode("utf-8")), []
            for s in sections:
                sb = len(s.encode("utf-8"))
                if cur and cur_bytes + sb > SIZE_LIMIT:
                    parts.append(cur)
                    cur, cur_bytes = [], len(f"# {title}\n\n".encode("utf-8"))
                cur.append(s)
                cur_bytes += sb
            if cur: parts.append(cur)
            single = len(parts) == 1
            for i, secs in enumerate(parts, start=1):
                stem = safe if single else f"{safe}_{i}"
                header = h1 if i == 1 else f"# {title}\n\n"
                write_file(os.path.join(OUT_DIR, stem + ".md"), to_simplified(header + "".join(secs)))
                total_files += 1

    print(f"蒙学: files={total_files}")


if __name__ == "__main__":
    main()
