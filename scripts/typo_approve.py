#!/usr/bin/env python3
"""typo_approve.py - 从候选生成确认清单（approved.jsonl）

规则：剔除校验违规项（context 过短、before 不在正文、context 不含 before、after 非法），
其余全部进入确认清单。乱码类（before/after 含非汉字字符）标记 garbled=true 单独放行。
"""

import json
import re
import sys
from pathlib import Path

DATA = Path(__file__).parent.parent / "data"
CHAPTER_DIR = DATA / "chapters"
CANDIDATE_DIR = DATA / "typo_candidates"
APPROVED = DATA / "typo_approved.jsonl"
MIN_CONTEXT = 15


def strip_punct(s: str) -> str:
    return re.sub(r"[\W_]+", "", s, flags=re.UNICODE)


def validate(issue: dict, txt: str) -> tuple[bool, str]:
    before, after, context = (
        issue.get("before", ""),
        issue.get("after", ""),
        issue.get("context", ""),
    )
    if not isinstance(before, str) or not before:
        return False, "before 为空或非字符串"
    if not isinstance(after, str) or not after:
        return False, "after 为空或非字符串"
    if not isinstance(context, str) or len(context) < MIN_CONTEXT:
        return False, f"context 过短 ({len(context)}字)"
    if before not in txt:
        return False, "before 不在原正文中"
    if before not in context:
        return False, "context 不含 before"
    return True, "ok"


def is_garbled(issue: dict) -> bool:
    """乱码类：before/after 的非汉字部分不一致（含 ASCII 混入、** 等）"""
    before, after = issue.get("before", ""), issue.get("after", "")
    non_han = lambda s: re.sub(r"[\u4e00-\u9fff]", "", s)
    return non_han(before) != non_han(after)


def main():
    entries = []
    skipped = 0
    for f in sorted(CANDIDATE_DIR.glob("*.json")):
        cid = f.stem
        chapter = json.loads((CHAPTER_DIR / f"{cid}.json").read_text())
        txt = chapter["txt"]
        try:
            data = json.loads(f.read_text())
        except json.JSONDecodeError:
            print(f"候选文件解析失败: {f}", file=sys.stderr)
            sys.exit(1)
        for i, issue in enumerate(data.get("issues", [])):
            ok, reason = validate(issue, txt)
            if not ok:
                skipped += 1
                print(f"  剔除 [{cid}]#{i}: {reason}")
                continue
            entries.append(
                {
                    "chapterid": int(cid),
                    "before": issue["before"],
                    "after": issue["after"],
                    "type": issue.get("type", ""),
                    "reason": issue.get("reason", ""),
                    "context": issue["context"],
                    "garbled": is_garbled(issue),
                }
            )
    APPROVED.write_text(
        "\n".join(json.dumps(e, ensure_ascii=False) for e in entries) + "\n"
    )
    garbled = sum(1 for e in entries if e["garbled"])
    print(
        f"approved.jsonl 生成: {len(entries)} 条（剔除 {skipped} 条违规，乱码类 {garbled} 条）"
    )


if __name__ == "__main__":
    main()
