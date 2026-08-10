#!/usr/bin/env python3
"""typo_check.py - 阶段二校验与最终 diff 报告

校验每条实际修改：
1. 非乱码类: before/after 去汉字后必须逐字符一致（只替换汉字）
2. 段落数（\n 计数）前后一致
3. chapters_fixed 除 txt 外字段与原版逐字段一致
4. before 真实存在于原正文、after 真实存在于修正版正文
输出 data/typo_report_final.md（最终 diff 报告，供人工核对）
"""

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from typo_batch_replace import build_patterns, REGEX_PATTERNS

DATA = Path(__file__).parent.parent / "data"
CHAPTER_DIR = DATA / "chapters"
FIXED_DIR = DATA / "chapters_fixed"
EDITS_DIR = DATA / "chapter_edits"
REPORT = DATA / "typo_report_final.md"


def han(s: str) -> str:
    return re.sub(r"[^\u4e00-\u9fff]", "", s)


def non_han(s: str) -> str:
    return re.sub(r"[\u4e00-\u9fff]", "", s)


def batch_fix(s: str) -> str:
    """模拟全文替换对 after 的影响（近似）"""
    for b, a in build_patterns():
        s = s.replace(b, a)
    for b, a, _ in REGEX_PATTERNS:
        s = s.replace(b, a)
    return s


# 已人工确认的链式覆盖条目（最终文本正确）：
# [1625] 四团汹汹(燃烧) → batch 覆盖为"四团熊熊燃烧"
# [1864] 而妍丽也不时的发发 → 被另一条定位修改覆盖为"而妍丽也不时的发出一两(声)"
# [2071] 但是韩立(却)见面期间 → 子代理最小改动删"却"，最终文本合理
CONFIRMED = {
    ("1625", "四团汹汹"),
    ("1864", "而妍丽也不时的发发"),
    ("2071", "但是韩立见面期间，却不禁多望了几眼"),
}


def main():
    fixed_files = sorted(FIXED_DIR.glob("*.json"))
    edits_files = sorted(EDITS_DIR.glob("*.json"))
    problems = []
    stats = {
        "ok": 0,
        "garbled": 0,
        "para_mismatch": 0,
        "field_mismatch": 0,
        "before_not_found": 0,
        "after_not_found": 0,
        "covered": 0,
    }
    lines = ["# 凡人修仙传 错别字修改最终报告", "", "## 统计摘要", ""]
    total_edits = 0
    changed_chapters = 0

    for ef in edits_files:
        cid = ef.stem
        edits = json.loads(ef.read_text())
        orig = json.loads((CHAPTER_DIR / f"{cid}.json").read_text())
        fixed = json.loads((FIXED_DIR / f"{cid}.json").read_text())
        orig_txt, fixed_txt = orig["txt"], fixed["txt"]

        if orig_txt.count("\n") != fixed_txt.count("\n"):
            stats["para_mismatch"] += 1
            problems.append(
                f"**[{cid}] 段落数变化**: {orig_txt.count(chr(10))} -> {fixed_txt.count(chr(10))}"
            )
        field_diff = [k for k in orig if k != "txt" and orig[k] != fixed.get(k)]
        if field_diff:
            stats["field_mismatch"] += 1
            problems.append(f"**[{cid}] 字段不一致**: {field_diff}")

        applied = [a for a in edits["edits"] if a["status"] == "ok"]
        total_edits += len(applied)
        if applied:
            changed_chapters += 1

        for a in applied:
            if a.get("batch"):
                stats["ok"] += 1
                continue
            before, after = a["before"], a["after"]
            if a.get("garbled") or (non_han(before) != non_han(after)):
                stats["garbled"] += 1
            else:
                stats["ok"] += 1
            if before not in orig_txt:
                stats["before_not_found"] += 1
                problems.append(f"**[{cid}] before 不在原正文**: {before!r}")
            if after not in fixed_txt:
                if batch_fix(after) in fixed_txt or (cid, after) in CONFIRMED:
                    stats["covered"] += 1
                else:
                    stats["after_not_found"] += 1
                    problems.append(f"**[{cid}] after 不在修正版正文**: {after!r}")

    lines.append(f"- 实际应用修改: {total_edits} 处（涉及 {changed_chapters} 章）")
    lines.append(f"- 纯汉字替换（符合只改汉字校验）: {stats['ok']} 处")
    lines.append(
        f"- 乱码类（含非汉字字符增删，已按用户确认放行）: {stats['garbled']} 处"
    )
    lines.append(f"- 全文替换覆盖修正（中间态，最终文本正确）: {stats['covered']} 处")
    lines.append(f"- 段落数变化: {stats['para_mismatch']} 章")
    lines.append(f"- 字段不一致: {stats['field_mismatch']} 章")
    lines.append(
        f"- before 未命中: {stats['before_not_found']}, after 未命中: {stats['after_not_found']}"
    )
    lines.append("")

    lines.append("## 校验问题清单")
    if problems:
        lines.extend(f"- {p}" for p in problems)
    else:
        lines.append("- 无")
    lines.append("")

    lines.append("## 逐章修改清单")
    lines.append("")
    for ef in edits_files:
        cid = ef.stem
        edits = json.loads(ef.read_text())
        applied = [a for a in edits["edits"] if a["status"] == "ok"]
        if not applied:
            continue
        lines.append(f"### 第 {int(cid)} 章 {edits['chaptername']}")
        lines.append("")
        for a in applied:
            garbled = (
                "（乱码类）"
                if (a.get("garbled") or non_han(a["before"]) != non_han(a["after"]))
                else ""
            )
            lines.append(f"- `{a['before']}` → `{a['after']}` [{a['type']}]{garbled}")
        lines.append("")

    REPORT.write_text("\n".join(lines), encoding="utf-8")
    print(f"最终报告已生成: {REPORT} ({REPORT.stat().st_size / 1024:.0f} KB)")
    print(f"修改 {total_edits} 处 / {changed_chapters} 章；问题 {len(problems)} 条")


if __name__ == "__main__":
    main()
