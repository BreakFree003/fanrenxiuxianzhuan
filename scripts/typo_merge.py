#!/usr/bin/env python3
"""typo_merge.py - 候选汇总、schema 校验、候选报告生成

输入：data/typo_candidates/*.json
输出：data/typo_report.md（摘要 + 高频统计 + 逐章清单 + 无问题章节 + 违规项）
"""

import json
import sys
from collections import Counter
from pathlib import Path

DATA = Path(__file__).parent.parent / "data"
CHAPTER_DIR = DATA / "chapters"
CANDIDATE_DIR = DATA / "typo_candidates"
REPORT = DATA / "typo_report.md"

VALID_TYPES = {"错别字", "形近错字", "漏字", "不通顺"}


def load_chapter(cid):
    f = CHAPTER_DIR / f"{cid:04d}.json"
    if not f.exists():
        return None
    return json.loads(f.read_text())


def validate_candidate(cid, cand, chapter):
    """返回违规列表；空列表 = 通过"""
    problems = []
    t = cand.get("type")
    if t not in VALID_TYPES:
        problems.append(f"type 非法: {t!r}")
    before = cand.get("before")
    after = cand.get("after")
    context = cand.get("context")
    if not before or not isinstance(before, str):
        problems.append("before 为空或非字符串")
    if not after or not isinstance(after, str):
        problems.append("after 为空或非字符串")
    if not context or len(context) < 10:
        problems.append(f"context 过短: {context!r}")
    elif before and before not in context:
        problems.append(f"context 不含 before: before={before!r}")
    if before and before not in chapter["txt"]:
        problems.append(f"before 不在原正文中: {before!r}")
    return problems


def main():
    if not CANDIDATE_DIR.exists():
        print("typo_candidates 目录不存在", file=sys.stderr)
        sys.exit(1)

    cand_files = sorted(CANDIDATE_DIR.glob("*.json"))
    per_chapter = {}
    violations = []
    warnings = []
    total_issues = 0
    type_counter = Counter()
    pattern_counter = Counter()

    for f in cand_files:
        cid = f.stem
        try:
            data = json.loads(f.read_text())
        except json.JSONDecodeError as e:
            violations.append(f"**[{cid}] JSON 解析失败**: {e}")
            continue
        chapter = load_chapter(int(cid))
        if chapter is None:
            violations.append(f"**[{cid}] 原章节文件不存在**")
            continue
        if data.get("chapterid") != int(cid):
            violations.append(f"**[{cid}] chapterid 字段与文件名不一致**")
        if data.get("chaptername") != chapter.get("chaptername"):
            warnings.append(
                f"[{cid}] chaptername 与章节文件不一致（数据源标题错位，已忽略）: "
                f"{data.get('chaptername')!r}"
            )
        issues = data.get("issues", [])
        if not isinstance(issues, list):
            violations.append(f"**[{cid}] issues 非数组**")
            issues = []
        for i, cand in enumerate(issues):
            probs = validate_candidate(cid, cand, chapter)
            if probs:
                violations.append(f"**[{cid}] 候选#{i}**: {'; '.join(probs)}")
            else:
                type_counter[cand["type"]] += 1
                pattern_counter[(cand["before"], cand["after"])] += 1
        total_issues += len(issues)
        per_chapter[cid] = issues

    chapter_ids = sorted(c for c in per_chapter)
    chapters_with_issues = [c for c in chapter_ids if per_chapter[c]]
    chapters_clean = [c for c in chapter_ids if not per_chapter[c]]

    lines = []
    lines.append("# 凡人修仙传 错别字候选报告\n")
    lines.append("## 统计摘要")
    lines.append(f"- 已处理候选文件: {len(cand_files)} 章")
    lines.append(f"- 候选总数: {total_issues} 处")
    lines.append(f"- 有候选的章节: {len(chapters_with_issues)} 章")
    lines.append(f"- 无候选的章节: {len(chapters_clean)} 章")
    lines.append(f"- 校验违规项: {len(violations)} 条（另有警告 {len(warnings)} 条）")
    if type_counter:
        lines.append("\n按类型分布:")
        for t, n in type_counter.most_common():
            lines.append(f"  - {t}: {n}")
    lines.append("\n## 高频错字统计（Top 30，按 before→after 分组）")
    lines.append("| 原文 | 改后 | 次数 |")
    lines.append("|---|---|---|")
    for (b, a), n in pattern_counter.most_common(30):
        lines.append(f"| {b} | {a} | {n} |")
    lines.append("\n## 逐章候选清单")
    for cid in chapter_ids:
        chapter = load_chapter(int(cid))
        if chapter is None:
            continue
        name = chapter["chaptername"]
        issues = per_chapter[cid]
        if not issues:
            continue
        lines.append(f"\n### {name}（{len(issues)} 处）")
        for i, cand in enumerate(issues, 1):
            lines.append(
                f"{i}. [{cand['type']}] `{cand['before']}` → `{cand['after']}`"
            )
            lines.append(f"   - 理由: {cand.get('reason', '')}")
            lines.append(f"   - 上下文: …{cand.get('context', '')}…")
    lines.append("\n## 无候选章节（疑似无问题）")
    lines.append(f"共 {len(chapters_clean)} 章: " + ", ".join(chapters_clean) + "\n")
    if violations:
        lines.append("## 校验违规项（需人工处理）")
        lines.extend(f"- {v}" for v in violations)
    if warnings:
        lines.append("\n## 警告（不影响候选有效性）")
        lines.extend(f"- {w}" for w in warnings)
    lines.append("")

    REPORT.write_text("\n".join(lines))
    print(f"报告已生成: {REPORT} ({REPORT.stat().st_size / 1024:.1f} KB)")
    print(
        f"候选 {total_issues} 处, 违规 {len(violations)} 条, 无候选 {len(chapters_clean)} 章"
    )


if __name__ == "__main__":
    main()
