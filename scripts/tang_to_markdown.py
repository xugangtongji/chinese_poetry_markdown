#!/usr/bin/env python3
"""Convert 全唐诗/poet.tang.*.json → markdown/全唐诗/<rank>_<author>_<range>.md.

Authors are ranked by descending poem count (4-digit prefix in filename).
Within each author, poems are sorted by descending fame (sum of search-engine
hits from rank/poet/poet.tang.rank.*.json, recovered from git commit 99ebbef).
Single-poem authors use <rank>_<author>_<title>.md.
"""
from __future__ import annotations

import glob
import json
import os
import re
import shutil
import subprocess
from collections import OrderedDict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_DIR = os.path.join(ROOT, "全唐诗")
OUT_DIR = os.path.join(ROOT, "markdown", "全唐诗")
RANK_COMMIT = "99ebbef"
SIZE_LIMIT = 200_000
MAX_TITLE_CHARS = 60

UNSAFE = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


def sanitize(name: str) -> str:
    return UNSAFE.sub("_", name).strip() or "佚名"


def truncate_title(t: str) -> str:
    return t if len(t) <= MAX_TITLE_CHARS else t[:MAX_TITLE_CHARS] + "…"


def chunk_strides() -> list[int]:
    strides = []
    for p in glob.glob(os.path.join(SRC_DIR, "poet.tang.*.json")):
        m = re.search(r"poet\.tang\.(\d+)\.json$", p)
        if m:
            strides.append(int(m.group(1)))
    return sorted(strides)


def load_poems_chunk(stride: int) -> list[dict]:
    with open(os.path.join(SRC_DIR, f"poet.tang.{stride}.json"), encoding="utf-8") as f:
        return json.load(f)


def load_rank_chunk(stride: int) -> list[dict] | None:
    try:
        out = subprocess.check_output(
            ["git", "show", f"{RANK_COMMIT}:rank/poet/poet.tang.rank.{stride}.json"],
            cwd=ROOT,
            stderr=subprocess.DEVNULL,
        )
    except subprocess.CalledProcessError:
        return None
    return json.loads(out)


def fame_score(rec: dict | None) -> int:
    if not rec:
        return 0
    return sum(int(rec.get(k) or 0) for k in ("baidu", "so360", "bing", "bing_en", "google"))


def render_poem(p: dict) -> str:
    title = (p.get("title") or "").strip() or "无题"
    paras = [s.strip() for s in (p.get("paragraphs") or []) if s and s.strip()]
    if not paras:
        return ""
    return f"## {title}\n\n" + "\n\n".join(paras) + "\n\n"


def main() -> None:
    with open(os.path.join(SRC_DIR, "authors.tang.json"), encoding="utf-8") as f:
        authors_desc = {r["name"]: (r.get("desc") or "").strip() for r in json.load(f)}

    by_author: "OrderedDict[str, list[tuple[dict, int]]]" = OrderedDict()
    total_poems = 0
    skipped_empty_body = 0
    skipped_bad_render = 0
    empty_titles_filled = 0
    missing_rank_chunks: list[int] = []

    for stride in chunk_strides():
        poems = load_poems_chunk(stride)
        ranks = load_rank_chunk(stride)
        if ranks is None:
            missing_rank_chunks.append(stride)
            ranks = [None] * len(poems)
        if len(ranks) != len(poems):
            print(f"WARN: alignment off at stride {stride}: poems={len(poems)} ranks={len(ranks)}")
            ranks = ranks[: len(poems)] + [None] * (len(poems) - len(ranks))

        for poem, rank in zip(poems, ranks):
            paras = [s for s in (poem.get("paragraphs") or []) if s and s.strip()]
            if not paras:
                skipped_empty_body += 1
                continue
            if not (poem.get("title") or "").strip():
                empty_titles_filled += 1
            author = (poem.get("author") or "").strip() or "佚名"
            by_author.setdefault(author, []).append((poem, fame_score(rank)))
            total_poems += 1

    ranked_authors = sorted(
        by_author.items(), key=lambda kv: -len(kv[1])
    )
    width = max(4, len(str(len(ranked_authors))))

    if os.path.isdir(OUT_DIR):
        shutil.rmtree(OUT_DIR)
    os.makedirs(OUT_DIR)

    files_written = 0
    authors_without_desc = 0
    collisions: list[tuple[str, str]] = []
    oversize: list[tuple[str, int]] = []
    used_filenames: set[str] = set()

    for idx, (author, poems_with_fame) in enumerate(ranked_authors, start=1):
        rank_prefix = f"{idx:0{width}d}"
        safe_author = sanitize(author)
        desc = authors_desc.get(author, "")
        if not desc:
            authors_without_desc += 1

        intro_block = f"# {author}\n\n" + (desc + "\n\n" if desc else "")
        just_h1 = f"# {author}\n\n"

        poems_sorted = sorted(poems_with_fame, key=lambda pf: -pf[1])

        if len(poems_sorted) == 1:
            poem, _ = poems_sorted[0]
            body = render_poem(poem)
            if not body:
                skipped_bad_render += 1
                continue
            title = (poem.get("title") or "").strip() or "无题"
            safe_title = sanitize(truncate_title(title))
            stem = f"{rank_prefix}_{safe_author}_{safe_title}"
            if stem in used_filenames:
                pid = poem.get("id", "")
                stem = f"{stem}-{pid[:5] if pid else 'x'}"
                collisions.append((author, stem))
            used_filenames.add(stem)
            path = os.path.join(OUT_DIR, stem + ".md")
            with open(path, "w", encoding="utf-8") as f:
                f.write(intro_block + body)
            files_written += 1
            continue

        rendered: list[tuple[int, str, int]] = []  # (1-based index, block, bytes)
        for i, (poem, _) in enumerate(poems_sorted, start=1):
            block = render_poem(poem)
            if not block:
                skipped_bad_render += 1
                continue
            rendered.append((i, block, len(block.encode("utf-8"))))

        if not rendered:
            continue

        parts: list[tuple[int, int, list[str]]] = []
        current: list[str] = []
        current_indices: list[int] = []
        current_bytes = len(intro_block.encode("utf-8"))
        for i, block, blen in rendered:
            if current and current_bytes + blen > SIZE_LIMIT:
                parts.append((current_indices[0], current_indices[-1], current))
                current = []
                current_indices = []
                current_bytes = len(just_h1.encode("utf-8"))
            current.append(block)
            current_indices.append(i)
            current_bytes += blen
        if current:
            parts.append((current_indices[0], current_indices[-1], current))

        for part_num, (lo, hi, blks) in enumerate(parts, start=1):
            header = intro_block if part_num == 1 else just_h1
            stem = f"{rank_prefix}_{safe_author}_{lo}_{hi}"
            if stem in used_filenames:
                stem = f"{stem}-dup{part_num}"
                collisions.append((author, stem))
            used_filenames.add(stem)
            content = header + "".join(blks)
            path = os.path.join(OUT_DIR, stem + ".md")
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
            files_written += 1
            size = len(content.encode("utf-8"))
            if size > SIZE_LIMIT + 10_000:
                oversize.append((os.path.basename(path), size))

    print(f"authors:            {len(by_author)}")
    print(f"poems rendered:     {total_poems}")
    print(f"empty titles→无题:  {empty_titles_filled}")
    print(f"skipped empty body: {skipped_empty_body}")
    print(f"skipped bad render: {skipped_bad_render}")
    print(f"files written:      {files_written}")
    print(f"authors w/o desc:   {authors_without_desc}")
    if missing_rank_chunks:
        print(f"missing rank chunks: {len(missing_rank_chunks)} -> {missing_rank_chunks[:5]}")
    if collisions:
        print(f"filename collisions: {len(collisions)}")
        for a, n in collisions[:10]:
            print(f"  {a!r} -> {n}")
    if oversize:
        print(f"oversize files (> {SIZE_LIMIT + 10_000}B): {len(oversize)}")
        for n, s in oversize[:10]:
            print(f"  {n}: {s}")


if __name__ == "__main__":
    main()
