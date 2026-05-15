# chinese_poetry_markdown

中国古典诗词与典籍的 Markdown 格式仓库，从 [chinese-poetry/chinese-poetry](https://github.com/chinese-poetry/chinese-poetry) 的 JSON 数据集衍生而来，涵盖唐诗、宋词、元曲、五代词、楚辞、诗经、论语、四书五经、蒙学等十二个文集，共 **2,791 个 Markdown 文件 / 24 MB / 9.36 万首诗文**。

每个文件 ≤ 200 KB，方便检索、嵌入应用、或在编辑器里直接翻阅。

## 内容概览

| 文集 | 文件数 | 收录数 | 备注 |
|---|---:|---:|---|
| [全唐诗](全唐诗) | 1,795 | 60,146 | 全唐诗 + 御定全唐詩 合并去重 |
| [宋词](宋词) | 734 | 21,050 | 含千家词 |
| [元曲](元曲) | 196 | 10,914 | 含千家曲 |
| [五代诗词](五代诗词) | 21 | 543 | 花间集 + 南唐二主词 |
| [纳兰性德](纳兰性德) | 1 | 257 | 单作者 |
| [曹操诗集](曹操诗集) | 1 | 26 | 单作者 |
| [楚辞](楚辞) | 17 | 65 | 按 section 分文件 |
| [诗经](诗经) | 6 | 305 | 按 chapter（国风/小雅/大雅/颂） |
| [论语](论语) | 1 | 20 | 全 20 篇合并 |
| [四书五经](四书五经) | 3 | 16 | 大学 / 中庸 / 孟子 |
| [幽梦影](幽梦影) | 1 | 219 | 含张潮原文与历代评注 |
| [蒙学](蒙学) | 15 | 44 | 三字经、千字文、百家姓、古文观止等 |
| **合计** | **2,791** | **93,605** | |

## 文件命名约定

### 作者类（唐诗、宋词、元曲、五代诗词、纳兰、曹操）

- **多产作者**：`<排名>_<作者>_<诗数>.md`（如 [0002_杜甫_1_424.md](全唐诗/0002_杜甫_1_424.md)）。排名按该作者的诗词数量降序，前 4 位补零。
- **超过 200 KB 拆分时**：`<排名>_<作者>_<起>_<止>.md`，比如 `0001_白居易_1_493.md` ~ `0001_白居易_2968_3154.md` 表示白居易 3154 首诗被切成 5 份。
- **单首作者**：合并到 `千家诗_*.md` / `千家词_*.md` / `千家曲_*.md` / `千家集_*.md`，每首以 `## 题目（作者）` 标注。

### 典籍类（楚辞、诗经、论语、四书五经、幽梦影、蒙学）

- 按书本结构分文件（章/卷/部分）。文件名直接用章节名，如 [国风.md](诗经/国风.md)、[离骚.md](楚辞/离骚.md)。
- 单文件如果还超 200 KB，再加 `_lo_hi` 切片后缀。

## 单文件内容格式

```markdown
# 作者名（或书名 / 章节名）

作者介绍（仅多文件作者的首份 md，从源 authors.json 取）

## 题目

诗句段落 1

诗句段落 2
...
```

千家诗/词/曲等合集中，每首诗标题加上作者：`## 题目（作者）`。

## 字符集

| 文集 | 字符集 |
|---|---|
| 全唐诗、蒙学、四书五经 | **简体**（用 `opencc` t2s 从源繁体转换） |
| 其他九个文集 | 沿用源数据形态（绝大多数为简体，少量繁体保留） |

> 数据集本身在繁简之间并不严格统一；上述简化处理仅针对源数据明显是繁体的三个文集，避免阅读时混淆。

## 去重与归一化

`全唐诗` 与 `御定全唐詩` 内容深度合并：

- 用 `opencc t2s` + 手工异体字表（劒→剑、徧→遍、斾→旆 等）+ 编辑距离 ≤ 1 的模糊匹配，做 5 字桶 + 16 字签名去重；
- 御定 4.3 万首中去重后新增了 2,711 首加入对应作者的桶；
- 作者别名映射（李世民 ↔ 太宗皇帝、明皇帝 ↔ 玄宗皇帝、無名氏 ↔ 佚名 等）防止同一人因不同书的称谓被拆成多个桶。

水墨唐诗（176 首名诗简体注解版）跳过未并入：基本都已在全唐诗中，强行并入会引入大量繁简同名重复。

## 重新生成

所有转换脚本位于 [scripts/](scripts/)。脚本读取每个文集目录下的源 JSON（如 `全唐诗/poet.tang.*.json`、`宋词/ci.song.*.json`），重生成同目录下的 `.md` 文件。源 JSON 不再随本仓库一起分发，需要时请从上游 [chinese-poetry/chinese-poetry](https://github.com/chinese-poetry/chinese-poetry) 拉取放入对应目录。

```bash
pip install opencc-python-reimplemented   # 简繁转换 + 去重需要

python scripts/tang_to_markdown.py        # 全唐诗（合并御定全唐詩）
python scripts/song_ci_to_markdown.py     # 宋词
python scripts/yuanqu_to_markdown.py      # 元曲
python scripts/wudai_to_markdown.py       # 五代诗词
python scripts/nalan_to_markdown.py       # 纳兰性德
python scripts/caocao_to_markdown.py      # 曹操诗集
python scripts/chuci_to_markdown.py       # 楚辞
python scripts/shijing_to_markdown.py     # 诗经
python scripts/lunyu_to_markdown.py       # 论语
python scripts/sishu_to_markdown.py       # 四书五经
python scripts/youmengying_to_markdown.py # 幽梦影
python scripts/mengxue_to_markdown.py     # 蒙学
```

脚本每次运行只会删除并重生成目标目录下的 `*.md`，源 JSON 等其他文件不会被动到。共享辅助函数在 [scripts/_common.py](scripts/_common.py)。

## 数据来源与许可

源 JSON 数据来自 [chinese-poetry/chinese-poetry](https://github.com/chinese-poetry/chinese-poetry)（MIT 协议）。本仓库的转换脚本与衍生 Markdown 同样以 [MIT](LICENSE) 协议发布。
