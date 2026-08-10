# 凡人修仙传 精校版

**作者：忘语** · 共 2456 章 · AI 全量错别字校正版

基于网络来源整理，2026-08 对全部 2456 章做了全量错别字校正（同音错字、漏字、不通顺处），共修正 25,260 处，校验问题 0 条，原文件全程未被修改（哈希快照验证）。

## 目录结构

| 路径 | 内容 |
|------|------|
| `data/chapters/` | 原始章节 JSON（2456 章，每章含标题与正文 `txt` 字段） |
| `data/chapters_fixed/` | 校正后的章节 JSON（仅替换 `txt` 字段，其余字段与原版一致） |
| `data/typo_report_final.md` | **v1 与 v2 的完整差异报告**（修改统计、高频错字模式、逐章 before→after 清单） |
| `data/chapters.json` `book.json` `txt_ref.json` | 站点元数据 / 书名信息 / 参考文本 |
| `scripts/` | 校正管线脚本（候选 → 确认 → 修改 → 校验 → 报告） |
| `build_epub.py` | 从章节 JSON 生成 EPUB（支持 `--chapter-dir` `--output` 参数） |

## 文件

| 格式 | 版本 | 说明 |
|------|------|------|
| [凡人修仙传.epub](凡人修仙传.epub) | v1 | 原始版本（12.4 MB） |
| [凡人修仙传v2.epub](凡人修仙传v2.epub) | v2 | 错别字校正版（12.4 MB） |

txt / mobi / pdf 可由脚本本地生成（见下）。

## v2 差异报告

v1 与 v2 的完整改动清单见 [data/typo_report_final.md](data/typo_report_final.md)：统计摘要 → 高频错字模式 → 逐章 before→after 清单。

## 本地生成成品

```bash
python3 scripts/build_txt.py --chapters-dir data/chapters_fixed --output 凡人修仙传v2.txt
python3 build_epub.py --chapter-dir data/chapters_fixed --output 凡人修仙传v2.epub
ebook-convert 凡人修仙传v2.epub 凡人修仙传v2.mobi
ebook-convert 凡人修仙传v2.epub 凡人修仙传v2.pdf --paper-size a4 --margin-top 30 --margin-bottom 30 --margin-left 40 --margin-right 40 --base-font-size 11
```

（`ebook-convert` 来自 [Calibre](https://calibre-ebook.com/)。）

## 重新执行校正管线

```bash
python3 scripts/typo_schedule.py       # 批次调度/对账
python3 scripts/typo_merge.py          # 候选汇总 → data/typo_report.md
python3 scripts/typo_approve.py        # 生成确认清单 data/typo_approved.jsonl
python3 scripts/typo_apply.py          # 按清单修改 → chapters_fixed + chapter_edits
python3 scripts/typo_batch_replace.py  # 高频模式全文替换（带边界）
python3 scripts/typo_check.py          # 一致性校验 → data/typo_report_final.md
```
