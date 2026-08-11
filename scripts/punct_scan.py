#!/usr/bin/env python3
"""punct_scan.py - 全书标点问题扫描(只读,输出候选清单)

检测两类问题:
A. 连续标点: 两个及以上标点连用(排除合法连用)。按组合分组输出。
B. 引号错误:
   B1 对话右双引号写成左单引号: “xxx。‘ 应为 “xxx。”
   B2 术语引号混用(左单右双): ‘xxx” 应为 ‘xxx’ 或 “xxx”
   B3 术语引号混用(左双右单): “xxx’ 应为 “xxx” 或 ‘xxx’
   B4 引号跨度异常/错位: 疑似右引号跑位(如 842 章案例)
   B5 章节级引号不闭合: 计数不平

输出: data/punct_candidates/ 每类一个 md 清单
用法: python3 scripts/punct_scan.py
"""

import json
import re
from pathlib import Path

DATA = Path(__file__).parent.parent / "data"
CHAPTER_DIR = DATA / "chapters_fixed"
OUT_DIR = DATA / "punct_candidates"
OUT_DIR.mkdir(exist_ok=True)

# 连续标点中被视为合法的组合(不在正文中报)
LEGAL_RUNS = {"……", "——", "···"}


def load_chapters():
    for f in sorted(CHAPTER_DIR.glob("*.json")):
        j = json.loads(f.read_text(encoding="utf-8"))
        yield int(f.stem), j.get("chaptername", ""), j.get("txt", "")


def ctx_line(txt, pos, before=25, after=45):
    s = max(0, pos - before)
    e = min(len(txt), pos + after)
    return txt[s:e].replace("\n", "⏎")


def scan_consecutive_punct():
    """A: 连续标点(按组合分组)"""
    pattern = re.compile(r"[，。、；：？！!?]{2,}")
    hits = []
    for cid, title, txt in load_chapters():
        for m in pattern.finditer(txt):
            run = m.group()
            if run in LEGAL_RUNS or run.startswith("……"):
                continue
            hits.append(
                {
                    "chapterid": cid,
                    "title": title,
                    "run": run,
                    "context": ctx_line(txt, m.start()),
                }
            )
    return hits


def scan_b1():
    """B1: 标点后跟 ‘ 且该 ‘ 后无配对 ’ —— 右双引号写成左单引号"""
    hits = []
    lead = re.compile(r"[。，！？!?]‘")
    for cid, title, txt in load_chapters():
        for m in lead.finditer(txt):
            pos = m.start()
            # 检查这个 ‘ 后面 40 字符内是否有配对 ’
            tail = txt[pos + 1 : pos + 41]
            if "’" not in tail:
                hits.append(
                    {
                        "chapterid": cid,
                        "title": title,
                        "run": m.group(),
                        "context": ctx_line(txt, pos, 30, 40),
                    }
                )
    return hits


def scan_b2():
    """B2: ‘xxx” 左单右双混用"""
    pattern = re.compile(r"‘[^‘’“”\n]{1,40}”")
    hits = []
    for cid, title, txt in load_chapters():
        for m in pattern.finditer(txt):
            hits.append(
                {
                    "chapterid": cid,
                    "title": title,
                    "run": m.group(),
                    "context": ctx_line(txt, m.start(), 20, 30),
                }
            )
    return hits


def scan_b3():
    """B3: “xxx’ 左双右单混用"""
    pattern = re.compile(r"“[^‘’“”\n]{1,40}’")
    hits = []
    for cid, title, txt in load_chapters():
        for m in pattern.finditer(txt):
            hits.append(
                {
                    "chapterid": cid,
                    "title": title,
                    "run": m.group(),
                    "context": ctx_line(txt, m.start(), 20, 30),
                }
            )
    return hits


def scan_b4():
    """B4: 单引号跨度 > 40 字符(疑似错位)"""
    hits = []
    for cid, title, txt in load_chapters():
        start = -1
        for i, c in enumerate(txt):
            if c == "‘":
                if start == -1:
                    start = i
            elif c == "’" and start != -1:
                span = i - start
                if span > 40:
                    hits.append(
                        {
                            "chapterid": cid,
                            "title": title,
                            "span": span,
                            "context": ctx_line(txt, start, 15, 60),
                        }
                    )
                start = -1
    return hits


def scan_b5():
    """B5: 章节级单引号/双引号计数不平"""
    hits = []
    for cid, title, txt in load_chapters():
        for q, name in (("‘", "单引号"), ("“", "双引号")):
            other = "’" if q == "‘" else "”"
            l = txt.count(q)
            r = txt.count(other)
            if l != r:
                hits.append(
                    {
                        "chapterid": cid,
                        "title": title,
                        "kind": name,
                        "left": l,
                        "right": r,
                        "diff": l - r,
                    }
                )
    return hits


def write_md(name, header, rows, fmt):
    out = OUT_DIR / f"{name}.md"
    lines = [f"# {header}", "", f"共 {len(rows)} 处", ""]
    for i, row in enumerate(rows, 1):
        lines.append(f"## {i}. {fmt(row)}")
        lines.append("")
    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"{name}: {len(rows)} 处 -> {out}")


def main():
    a = scan_consecutive_punct()
    b1 = scan_b1()
    b2 = scan_b2()
    b3 = scan_b3()
    b4 = scan_b4()
    b5 = scan_b5()

    # A 类按组合分组
    from collections import Counter

    groups = Counter(r["run"] for r in a)
    lines = [f"# 连续标点问题", "", f"共 {len(a)} 处", "", "## 按组合分组", ""]
    for run, cnt in groups.most_common():
        lines.append(f"- `{run}`: {cnt} 处")
    lines.append("")
    lines.append("## 明细")
    lines.append("")
    for i, r in enumerate(a, 1):
        lines.append(f"## {i}. 第{r['chapterid']}章 {r['title']} — 连用 `{r['run']}`")
        lines.append(f"…{r['context']}…")
        lines.append("")
    (OUT_DIR / "A_连续标点.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"A 连续标点: {len(a)} 处")

    write_md(
        "B1_对话右引号写成左引号",
        "对话右双引号写成左单引号",
        b1,
        lambda r: (
            f"第{r['chapterid']}章 {r['title']} — `{r['run']}` — …{r['context']}…"
        ),
    )
    write_md(
        "B2_左单右双混用",
        "术语引号混用(左单右双 ‘xxx”)",
        b2,
        lambda r: (
            f"第{r['chapterid']}章 {r['title']} — `{r['run']}` — …{r['context']}…"
        ),
    )
    write_md(
        "B3_左双右单混用",
        "术语引号混用(左双右单 “xxx’)",
        b3,
        lambda r: (
            f"第{r['chapterid']}章 {r['title']} — `{r['run']}` — …{r['context']}…"
        ),
    )
    write_md(
        "B4_引号跨度异常",
        "单引号跨度>40字符(疑似错位)",
        b4,
        lambda r: (
            f"第{r['chapterid']}章 {r['title']} — 跨度{r['span']} — …{r['context']}…"
        ),
    )
    write_md(
        "B5_引号不闭合",
        "章节级引号计数不平(需人工甄别长引语/术语)",
        b5,
        lambda r: (
            f"第{r['chapterid']}章 {r['title']} — {r['kind']} 左{r['left']} 右{r['right']} (差{r['diff']:+d})"
        ),
    )

    print(f"B1 对话右引号写成左引号: {len(b1)}")
    print(f"B2 左单右双混用: {len(b2)}")
    print(f"B3 左双右单混用: {len(b3)}")
    print(f"B4 引号跨度异常: {len(b4)}")
    print(f"B5 引号不闭合: {len(b5)}")


if __name__ == "__main__":
    main()
