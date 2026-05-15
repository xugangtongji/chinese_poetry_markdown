#!/usr/bin/env python3
"""Convert 全唐诗/poet.tang.*.json + 御定全唐詩/json/*.json → markdown/全唐诗/.

御定 records are deduplicated against 全唐诗 by a fuzzy content signature
(opencc t2s + manual 異體字 map + edit-distance ≤1 within a 5-char bucket).
Tang emperor names in 御定 (e.g. 李世民) are aliased to the imperial-title
form used by 全唐诗 (e.g. 太宗皇帝) so the merge lands in the right bucket.

Multi-poem authors (>=2 poems): <rank>_<author>_<count>.md or
<rank>_<author>_<lo>_<hi>.md if size-split.
Single-poem authors: merged into 千家诗_<lo>_<hi>.md, poems rendered as
"## 题目（作者）". Empty title or body → skip.
"""
from __future__ import annotations

import glob
import json
import os
import re
import shutil
from collections import OrderedDict, defaultdict

try:
    from opencc import OpenCC
    _cc = OpenCC("t2s")
    def _to_simp(s: str) -> str: return _cc.convert(s)
except ImportError:
    def _to_simp(s: str) -> str: return s

# Convert all output text (content + filenames) to simplified Chinese.
simplify = _to_simp

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
QTS_DIR = os.path.join(ROOT, "全唐诗")
YD_DIR = os.path.join(ROOT, "御定全唐詩", "json")
OUT_DIR = os.path.join(ROOT, "全唐诗")
SIZE_LIMIT = 200_000

UNSAFE = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
PUNCT_WS = re.compile(r'[\s　，。！？、；：「」「」（）()\-—–·,.!?:;]+')

# Manual 異體字 normalization for variants opencc misses
VARIANT_MAP = str.maketrans({
    "劒": "剑", "劎": "剑",
    "徧": "遍",
    "巖": "岩",
    "羣": "群",
    "臺": "台", "檯": "台",
    "凜": "凛",
    "峯": "峰",
    "卻": "却",
    "斾": "旆",
    "勅": "敕", "勑": "敕",
    "彫": "雕", "鵰": "雕",
    "歎": "叹", "嘆": "叹",
    "綵": "彩",
    "甆": "瓷",
    "燬": "毁",
    "舘": "馆",
    "皷": "鼓",
    "于": "于", "於": "于",
    "尔": "尔", "爾": "尔",
    "罷": "罢",
    "歟": "欤",
    "裏": "里", "裡": "里",
    "弔": "吊",
})

# Author canonicalization: collapses Tang-emperor name forms and 全唐诗's own
# split between "<title>皇帝" / "<title>皇帝<name>" / "<name>" into one bucket.
# Applied to BOTH 全唐诗 and 御定 author fields.
AUTHOR_ALIAS = {
    # Tang emperor short-name (mostly seen in 御定) → 全唐诗 imperial-title form
    "李世民": "太宗皇帝",
    "李治": "高宗皇帝",
    "李顯": "中宗皇帝", "李显": "中宗皇帝",
    "李旦": "睿宗皇帝",
    "李隆基": "玄宗皇帝",
    "李亨": "肅宗皇帝",
    "李豫": "代宗皇帝",
    "李适": "德宗皇帝", "李適": "德宗皇帝",
    "李誦": "順宗皇帝", "李诵": "順宗皇帝",
    "李純": "憲宗皇帝", "李纯": "憲宗皇帝",
    "李恆": "穆宗皇帝", "李恒": "穆宗皇帝",
    "李湛": "敬宗皇帝",
    "李昂": "文宗皇帝",
    "李炎": "武宗皇帝",
    "李忱": "宣宗皇帝",
    "李漼": "懿宗皇帝",
    "李儇": "僖宗皇帝",
    "李曄": "昭宗皇帝", "李晔": "昭宗皇帝",
    "李柷": "哀帝",
    # 全唐诗's own compound-name duplicates
    "太宗皇帝李世民": "太宗皇帝",
    "高宗皇帝李治": "高宗皇帝",
    "順宗皇帝李誦": "順宗皇帝",
    "玄宗皇帝李隆基": "玄宗皇帝",
    "宣宗皇帝李忱": "宣宗皇帝",
    "德宗皇帝李适": "德宗皇帝",
    "明皇帝": "玄宗皇帝",  # 明皇帝 = 唐玄宗's posthumous title
    # Anonymous
    "無名氏": "佚名", "无名氏": "佚名",
}


def sanitize(name: str) -> str:
    return UNSAFE.sub("_", name).strip() or "佚名"


def normalize_body(poem: dict) -> str:
    paras = [s for s in (poem.get("paragraphs") or []) if s and s.strip()]
    if not paras:
        return ""
    joined = "".join(paras)
    joined = PUNCT_WS.sub("", joined)
    return _to_simp(joined.translate(VARIANT_MAP))


def edit_distance_le1(a: str, b: str) -> bool:
    if a == b:
        return True
    if abs(len(a) - len(b)) > 1:
        return False
    if len(a) == len(b):
        diffs = 0
        for ca, cb in zip(a, b):
            if ca != cb:
                diffs += 1
                if diffs > 1:
                    return False
        return True
    if len(a) > len(b):
        a, b = b, a
    i = j = d = 0
    while i < len(a) and j < len(b):
        if a[i] != b[j]:
            d += 1
            if d > 1:
                return False
            j += 1
        else:
            i += 1
            j += 1
    return True


def chunk_strides() -> list[int]:
    strides = []
    for p in glob.glob(os.path.join(QTS_DIR, "poet.tang.*.json")):
        m = re.search(r"poet\.tang\.(\d+)\.json$", p)
        if m:
            strides.append(int(m.group(1)))
    return sorted(strides)


def render_body(p: dict) -> str:
    paras = [s.strip() for s in (p.get("paragraphs") or []) if s and s.strip()]
    if not paras:
        return ""
    return "\n\n".join(paras) + "\n\n"


def split_by_size(items, header_bytes_first, header_bytes_rest, limit):
    parts = []
    cur, cur_idx, cur_bytes = [], [], header_bytes_first
    for i, block, blen in items:
        if cur and cur_bytes + blen > limit:
            parts.append((cur_idx[0], cur_idx[-1], cur))
            cur, cur_idx, cur_bytes = [], [], header_bytes_rest
        cur.append(block)
        cur_idx.append(i)
        cur_bytes += blen
    if cur:
        parts.append((cur_idx[0], cur_idx[-1], cur))
    return parts


def main() -> None:
    with open(os.path.join(QTS_DIR, "authors.tang.json"), encoding="utf-8") as f:
        authors_desc = {r["name"]: (r.get("desc") or "").strip() for r in json.load(f)}

    by_author: "OrderedDict[str, list[dict]]" = OrderedDict()
    total = empty_body = empty_title = 0
    qts_bucket: "dict[str, list[str]]" = defaultdict(list)

    for stride in chunk_strides():
        with open(os.path.join(QTS_DIR, f"poet.tang.{stride}.json"), encoding="utf-8") as f:
            for poem in json.load(f):
                paras = [s for s in (poem.get("paragraphs") or []) if s and s.strip()]
                if not paras:
                    empty_body += 1
                    continue
                if not (poem.get("title") or "").strip():
                    empty_title += 1
                    continue
                author_raw = (poem.get("author") or "").strip() or "佚名"
                author = AUTHOR_ALIAS.get(author_raw, author_raw)
                by_author.setdefault(author, []).append(poem)
                total += 1

                nb = normalize_body(poem)
                if len(nb) >= 8:
                    qts_bucket[nb[:5]].append(nb[:16])

    yd_total = yd_added = yd_skipped_body = yd_skipped_title = yd_aliased = 0
    yd_added_by_author: dict[str, int] = defaultdict(int)
    for path in sorted(glob.glob(os.path.join(YD_DIR, "*.json"))):
        with open(path, encoding="utf-8") as f:
            for poem in json.load(f):
                paras = [s for s in (poem.get("paragraphs") or []) if s and s.strip()]
                if not paras:
                    yd_skipped_body += 1
                    continue
                if not (poem.get("title") or "").strip():
                    yd_skipped_title += 1
                    continue
                yd_total += 1
                nb = normalize_body(poem)
                if len(nb) < 8:
                    continue
                my_sig = nb[:16]
                candidates = qts_bucket.get(nb[:5], [])
                if any(edit_distance_le1(my_sig, c) for c in candidates):
                    continue
                # not in 全唐诗 — add (aliasing author if applicable)
                author_raw = (poem.get("author") or "").strip() or "佚名"
                author = AUTHOR_ALIAS.get(author_raw, author_raw)
                if author != author_raw:
                    yd_aliased += 1
                # strip the leading "樂府雜曲：" / "橫吹曲辭：" path from title for cleaner rendering
                title = poem.get("title", "").strip()
                if "：" in title:
                    parts = [p.strip() for p in title.split("：") if p.strip()]
                    title = parts[-1] if parts else title
                cleaned = {
                    "author": author,
                    "title": title,
                    "paragraphs": poem.get("paragraphs", []),
                }
                by_author.setdefault(author, []).append(cleaned)
                qts_bucket[nb[:5]].append(my_sig)
                yd_added += 1
                yd_added_by_author[author] += 1

    multi = [(a, ps) for a, ps in by_author.items() if len(ps) >= 2]
    singles = [(a, ps[0]) for a, ps in by_author.items() if len(ps) == 1]
    multi.sort(key=lambda kv: -len(kv[1]))
    rank_width = max(4, len(str(len(multi))))

    if os.path.isdir(OUT_DIR):
        shutil.rmtree(OUT_DIR)
    os.makedirs(OUT_DIR)

    files_written = 0
    used: set[str] = set()
    oversize: list[tuple[str, int]] = []

    for idx, (author, poems) in enumerate(multi, start=1):
        prefix = f"{idx:0{rank_width}d}"
        safe_author = sanitize(simplify(author))
        desc = authors_desc.get(author, "")
        intro = f"# {author}\n\n" + (desc + "\n\n" if desc else "")
        just_h1 = f"# {author}\n\n"

        blocks = []
        for i, poem in enumerate(poems, start=1):
            body = render_body(poem)
            if not body:
                continue
            title = (poem.get("title") or "").strip()
            if not title:
                continue
            block = f"## {title}\n\n{body}"
            blocks.append((i, block, len(block.encode("utf-8"))))

        if not blocks:
            continue

        parts = split_by_size(
            blocks,
            header_bytes_first=len(intro.encode("utf-8")),
            header_bytes_rest=len(just_h1.encode("utf-8")),
            limit=SIZE_LIMIT,
        )
        single_part = len(parts) == 1
        for part_num, (lo, hi, blks) in enumerate(parts, start=1):
            header = intro if part_num == 1 else just_h1
            stem = f"{prefix}_{safe_author}_{hi}" if single_part else f"{prefix}_{safe_author}_{lo}_{hi}"
            if stem in used:
                stem = f"{stem}-dup{part_num}"
            used.add(stem)
            content = header + "".join(blks)
            path = os.path.join(OUT_DIR, stem + ".md")
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(simplify(content))
            files_written += 1
            size = len(content.encode("utf-8"))
            if size > SIZE_LIMIT + 10_000:
                oversize.append((os.path.basename(path), size))

    qjs_h1 = "# 千家诗\n\n"
    qjs_blocks = []
    for i, (author, poem) in enumerate(singles, start=1):
        body = render_body(poem)
        title = (poem.get("title") or "").strip()
        if not body or not title:
            continue
        block = f"## {title}（{author}）\n\n{body}"
        qjs_blocks.append((i, block, len(block.encode("utf-8"))))

    if qjs_blocks:
        qjs_parts = split_by_size(
            qjs_blocks,
            header_bytes_first=len(qjs_h1.encode("utf-8")),
            header_bytes_rest=len(qjs_h1.encode("utf-8")),
            limit=SIZE_LIMIT,
        )
        qjs_single = len(qjs_parts) == 1
        for part_num, (lo, hi, blks) in enumerate(qjs_parts, start=1):
            stem = f"千家诗_{hi}" if qjs_single else f"千家诗_{lo}_{hi}"
            content = qjs_h1 + "".join(blks)
            path = os.path.join(OUT_DIR, stem + ".md")
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(simplify(content))
            files_written += 1

    print(f"全唐诗 poems used:      {total}")
    print(f"全唐诗 skipped (title): {empty_title}")
    print(f"全唐诗 skipped (body):  {empty_body}")
    print(f"御定 poems considered:  {yd_total}")
    print(f"御定 skipped (title):   {yd_skipped_title}")
    print(f"御定 skipped (body):    {yd_skipped_body}")
    print(f"御定 added (after dedup): {yd_added}")
    print(f"御定 aliased authors:   {yd_aliased}")
    print(f"authors total:          {len(by_author)}")
    print(f"  multi-poem:           {len(multi)}")
    print(f"  single-poem:          {len(singles)}")
    print(f"files written:          {files_written}")
    print()
    print("Top 10 御定 contributions by author:")
    for a, c in sorted(yd_added_by_author.items(), key=lambda kv: -kv[1])[:10]:
        print(f"  {a:<15} +{c}")
    if oversize:
        print(f"oversize files: {len(oversize)}")


if __name__ == "__main__":
    main()
