#!/usr/bin/env python3
"""typo_apply.py - 按用户确认清单执行修改（阶段二）

流程：approved 来源校验 → 逐条 context 窗口定位替换 → 生成 chapters_fixed 与 chapter_edits

定位规则：before 必须在候选的 context 子串窗口内出现才替换；
出现 0 次 → 未命中；≥2 次 → 多命中待人工（绝不静默全量替换）。
"""

import json
import re
import sys
from pathlib import Path

DATA = Path(__file__).parent.parent / "data"
CHAPTER_DIR = DATA / "chapters"
CANDIDATE_DIR = DATA / "typo_candidates"
FIXED_DIR = DATA / "chapters_fixed"
EDITS_DIR = DATA / "chapter_edits"
APPROVED = DATA / "typo_approved.jsonl"

VALID_TYPES = {"错别字", "形近错字", "漏字", "不通顺"}

_norm = lambda s: re.sub(r"[^\u4e00-\u9fffA-Za-z0-9]+", "", s)


def locate_replace(txt: str, before: str, after: str, context: str) -> tuple[str, str]:
    """定位替换：乱码类用原始精确匹配，汉字类用归一化 context 窗口匹配"""
    if re.search(r"[^\u4e00-\u9fff]", before):
        count = txt.count(before)
        if count == 1:
            p = txt.find(before)
            return txt[:p] + after + txt[p + len(before) :], "ok"
        if count > 1:
            cpos = txt.find(context)
            if cpos != -1:
                window = txt[cpos : cpos + len(context)]
                n = window.count(before)
                if n == 1:
                    p = cpos + window.find(before)
                    return txt[:p] + after + txt[p + len(before) :], "ok"
                return txt, f"多命中待人工({n}处)"
            return txt, f"多命中待人工({count}处)"
        return txt, "未命中(before)"
    nctx = _norm(context)
    positions = []
    start = 0
    while True:
        p = txt.find(before, start)
        if p == -1:
            break
        win = txt[max(0, p - 80) : p + len(before) + 80]
        if nctx and nctx in _norm(win):
            positions.append(p)
        start = p + len(before)
    if len(positions) == 0:
        if txt.count(before) == 1:
            p = txt.find(before)
            return txt[:p] + after + txt[p + len(before) :], "ok"
        return txt, "未命中(context)"
    if len(positions) == 1:
        p = positions[0]
        return txt[:p] + after + txt[p + len(before) :], "ok"
    return txt, f"多命中待人工({len(positions)}处)"


def load_chapter(cid):
    f = CHAPTER_DIR / f"{cid:04d}.json"
    if not f.exists():
        return None
    return json.loads(f.read_text())


def verify_approved(entries):
    """来源校验：approved 每条必须与候选文件精确匹配"""
    bad = []
    for e in entries:
        cid = f"{e['chapterid']:04d}"
        f = CANDIDATE_DIR / f"{cid}.json"
        if not f.exists():
            bad.append(f"[{cid}] 候选文件不存在")
            continue
        try:
            cands = json.loads(f.read_text())["issues"]
        except Exception as ex:
            bad.append(f"[{cid}] 候选文件解析失败: {ex}")
            continue
        match = next(
            (
                c
                for c in cands
                if c.get("before") == e["before"]
                and c.get("after") == e["after"]
                and c.get("type") == e["type"]
                and c.get("context") == e["context"]
            ),
            None,
        )
        if match is None:
            bad.append(f"[{cid}] approved 与候选不匹配: {e['before']}→{e['after']}")
    return bad


def apply_entries(entries):
    """对每章应用修改，返回 (fixed, edits) 结果"""
    fixed_map = {}
    edits_map = {}
    for cid in sorted({e["chapterid"] for e in entries}):
        chapter = load_chapter(cid)
        if chapter is None:
            continue
        txt = chapter["txt"]
        applied = []
        for e in entries:
            if e["chapterid"] != cid:
                continue
            before, after, context = e["before"], e["after"], e["context"]
            txt, status = locate_replace(txt, before, after, context)
            applied.append(
                {
                    "before": before,
                    "after": after,
                    "type": e["type"],
                    "reason": e.get("reason", ""),
                    "status": status,
                    "garbled": e.get("garbled", False),
                }
            )
        fixed_map[cid] = txt
        edits_map[cid] = {
            "chapterid": cid,
            "chaptername": chapter["chaptername"],
            "edits": applied,
            "changed": any(a["status"] == "ok" for a in applied),
        }
    return fixed_map, edits_map


def main():
    if not APPROVED.exists():
        print(f"确认清单不存在: {APPROVED}", file=sys.stderr)
        sys.exit(1)
    entries = []
    for line in APPROVED.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            entries.append(json.loads(line))
        except json.JSONDecodeError as e:
            print(f"approved 行解析失败: {line[:60]}... ({e})", file=sys.stderr)
            sys.exit(1)

    bad = verify_approved(entries)
    if bad:
        print(f"来源校验失败 {len(bad)} 条，中止:")
        for b in bad[:20]:
            print(f"  - {b}")
        sys.exit(1)
    print(f"来源校验通过: {len(entries)} 条 approved")

    fixed_map, edits_map = apply_entries(entries)

    FIXED_DIR.mkdir(parents=True, exist_ok=True)
    EDITS_DIR.mkdir(parents=True, exist_ok=True)
    status_counter = {}
    changed = 0
    for cid, txt in fixed_map.items():
        chapter = load_chapter(cid)
        if chapter is None:
            continue
        fixed = dict(chapter)
        fixed["txt"] = txt
        (FIXED_DIR / f"{cid:04d}.json").write_text(
            json.dumps(fixed, ensure_ascii=False, indent=2)
        )
        edits = edits_map[cid]
        for a in edits["edits"]:
            status_counter[a["status"]] = status_counter.get(a["status"], 0) + 1
        if edits["changed"]:
            changed += 1
        (EDITS_DIR / f"{cid:04d}.json").write_text(
            json.dumps(edits, ensure_ascii=False, indent=2)
        )
    print(f"生成 chapters_fixed: {len(fixed_map)} 章（其中实际修改 {changed} 章）")
    print("应用状态分布:", dict(sorted(status_counter.items())))
    for chapter_file in sorted(CHAPTER_DIR.glob("*.json")):
        cid = int(chapter_file.stem)
        if cid not in fixed_map:
            chapter = load_chapter(cid)
            if chapter is None:
                continue
            (FIXED_DIR / f"{cid:04d}.json").write_text(
                json.dumps(chapter, ensure_ascii=False, indent=2)
            )
    total = len(list(FIXED_DIR.glob("*.json")))
    print(f"补齐无修改章节后 chapters_fixed 共: {total} 章")


if __name__ == "__main__":
    main()
