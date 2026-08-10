#!/usr/bin/env python3
"""typo_batch_replace.py - 高频模式全文替换（带记录）

安全清单从 approved 高频模式生成（≥5 次），排除歧义/专名模式。
替换结果追加记录到 chapter_edits，供最终报告完整呈现。
用法: 在 typo_apply.py 之后运行。
"""

import json
import re
import sys
from pathlib import Path
from collections import Counter

DATA = Path(__file__).parent.parent / "data"
CHAPTER_DIR = DATA / "chapters"
FIXED_DIR = DATA / "chapters_fixed"
EDITS_DIR = DATA / "chapter_edits"
APPROVED = DATA / "typo_approved.jsonl"

EXCLUDE = {
    ("一模", "一摸"),
    ("徒然", "陡然"),
    ("自付", "自忖"),
    ("自付", "自负"),
    ("注意", "主意"),
    ("大衍决", "大衍诀"),
    ("伪仙傫", "伪仙傀儡"),
    ("自持", "自恃"),
    ("法决", "法诀"),
    ("觉的", "觉得"),
    ("的的", "的"),
    ("跌跄", "踉跄"),
}
EXTRA = [("伪仙傫", "伪仙儡")]

# 危险模式：必须带边界正则（防止误伤合法词子串）
# 格式: (before, after, compiled_pattern)
REGEX_PATTERNS = [
    # "无法决定" 等：法决 前后带 无/方/定 时是"法+决"不是"法诀"
    ("法决", "法诀", re.compile(r"(?<![无方])(法决)(?!定)")),
    # "察觉的/不知不觉的/警觉的" 等：觉的 是"X觉+的"不是"觉得"
    ("觉的", "觉得", re.compile(r"(?<![察发警感知嗅自不觉])(觉的)")),
    # "的的确确/另有目的的"：的的 是"目的+的"或"的确"拆分
    ("的的", "的", re.compile(r"(?<![目有])(的的)(?!确)")),
    # "跌跌跄跄" 标准词：跌跄 后跟 跄 时不替换
    ("跌跄", "踉跄", re.compile(r"(跌跄)(?!跄)")),
]


def build_patterns():
    pat = Counter()
    for line in APPROVED.read_text(encoding="utf-8").splitlines():
        e = json.loads(line)
        if e.get("garbled"):
            continue
        pat[(e["before"], e["after"])] += 1
    multi = [(k, v) for k, v in pat.items() if v >= 5 and k not in EXCLUDE]
    by_before = {}
    for (b, a), v in multi:
        by_before.setdefault(b, set()).add(a)
    covered = set()
    bs = sorted(by_before, key=len)
    for b1 in bs:
        for b2 in bs:
            if b1 != b2 and b1 in b2:
                covered.add(b2)
    return [(b, sorted(by_before[b])[0]) for b in bs if b not in covered] + EXTRA


def main():
    patterns = build_patterns()
    print(f"安全全文替换模式: {len(patterns)} 个")
    total = 0
    for b, a in patterns:
        n = 0
        for f in sorted(FIXED_DIR.glob("*.json")):
            cid = int(f.stem)
            d = json.loads(f.read_text())
            cnt = d["txt"].count(b)
            if not cnt:
                continue
            d["txt"] = d["txt"].replace(b, a)
            f.write_text(json.dumps(d, ensure_ascii=False, indent=2))
            n += cnt
            _append_edit(cid, d, b, a, cnt)
        if n:
            print(f"  {b!r} → {a!r}: 替换 {n} 处")
        total += n
    print(f"共替换 {total} 处，记录已追加到 chapter_edits")


def main_with_regex():
    """带边界的正则模式替换（危险模式）"""
    total = 0
    for b, a, pat in REGEX_PATTERNS:
        n = 0
        for f in sorted(FIXED_DIR.glob("*.json")):
            cid = int(f.stem)
            d = json.loads(f.read_text())
            cnt = len(pat.findall(d["txt"]))
            if not cnt:
                continue
            d["txt"] = pat.sub(a, d["txt"])
            f.write_text(json.dumps(d, ensure_ascii=False, indent=2))
            n += cnt
            _append_edit(cid, d, b, a, cnt)
        if n:
            print(f"  {b!r} → {a!r}（正则边界）: 替换 {n} 处")
        total += n
    print(f"正则模式共替换 {total} 处")


def _append_edit(cid, d, b, a, cnt):
    ef = EDITS_DIR / f"{cid:04d}.json"
    if ef.exists():
        edits = json.loads(ef.read_text())
    else:
        edits = {
            "chapterid": cid,
            "chaptername": d.get("chaptername", ""),
            "edits": [],
        }
    edits["edits"].append(
        {
            "before": b,
            "after": a,
            "type": "错别字",
            "reason": f"高频模式全文替换（{cnt} 处）",
            "status": "ok",
            "garbled": False,
            "batch": True,
        }
    )
    ef.write_text(json.dumps(edits, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
    main_with_regex()
