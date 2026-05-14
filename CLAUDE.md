# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository purpose

`chinese-poetry` is an open-source classical Chinese poetry and literature database distributed as UTF-8 JSON. Scale: ~55K Tang poems, ~260K Song poems, ~21K Song ci (lyric poems), plus canonical works (论语, 诗经, 四书五经, etc.) and dynasty/author-specific collections. Data was web-scraped. This checkout is **data-only** — the previous Python loader, Node rank scraper, analytics images, and pytest validator have been removed; what remains is the JSON content. MIT-licensed.

## Commands

There is no build, no tests, no installable code in this checkout. To work with the data, parse the JSON files directly (any language with UTF-8 JSON support).

[.travis.yml](.travis.yml) is **stale** — it references `requirements.txt` and `pytest` (i.e. `test_poetry.py`), none of which exist anymore. Don't rely on it; either fix it or delete it as part of any cleanup PR.

## Architecture

All content lives in top-level directories whose names are Chinese (UTF-8). Always quote them in shell.

**Chunked collections** (large; split by id stride 1000):

- [全唐诗/](全唐诗/) — Tang + Song poems as `poet.tang.N.json` / `poet.song.N.json`, plus `authors.tang.json` / `authors.song.json`.
- [宋词/](宋词/) — Song ci as `ci.song.N.json`, plus `author.song.json`. Note: this dir also contains a sqlite `ci.db` and helper scripts (`UpdateCi.py`, `main.py`) that are tooling, not content.

**Single-file collections**: [元曲/](元曲/), [楚辞/](楚辞/), [诗经/](诗经/), [论语/](论语/), [四书五经/](四书五经/), [蒙学/](蒙学/), [幽梦影/](幽梦影/), [纳兰性德/](纳兰性德/), [曹操诗集/](曹操诗集/), [水墨唐诗/](水墨唐诗/), [御定全唐詩/](御定全唐詩/), [五代诗词/](五代诗词/).

**Record shape varies across collections** — the most common footgun. The field that holds the poem body is not the same everywhere:

| Body field    | Collections |
|---------------|-------------|
| `paragraphs`  | Tang/Song poems (全唐诗), Song ci (宋词, also has `rhythmic` = 词牌名), 元曲, 论语, 四书五经, 蒙学, 五代诗词, 御定全唐詩, 水墨唐诗, 曹操诗集 |
| `content`     | 楚辞, 诗经, 幽梦影 |
| `para`        | 纳兰性德 |

Verify the field by reading the first record of any file before writing extraction code — some sub-files inside 四书五经 and 蒙学 use non-standard structures and need special handling.

## Conventions & gotchas

- Chinese directory names must be quoted in shell; ensure the locale supports UTF-8.
- Data mixes simplified and traditional Chinese; some filenames are traditional (e.g. `御定全唐詩`). Do not silently normalize.
- Inside [宋词/](宋词/), the sqlite `ci.db` and `*.py` helpers are tooling, not data.
- Data is web-scraped and not perfectly clean. Corrections should cite a source per the [wiki contribution guidelines](https://github.com/chinese-poetry/chinese-poetry/wiki/参与贡献规范).
