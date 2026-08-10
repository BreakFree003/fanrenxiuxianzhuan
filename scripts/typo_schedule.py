#!/usr/bin/env python3
"""typo_schedule.py - 批次调度与状态管理

批次清单：2456 章按 20 章/批分成 123 批
状态表：data/typo_progress.json（pending/running/done/failed）
支持断点续跑与对账。
"""

import json
import sys
from pathlib import Path

DATA = Path(__file__).parent.parent / "data"
CHAPTER_DIR = DATA / "chapters"
CANDIDATE_DIR = DATA / "typo_candidates"
PROGRESS_FILE = DATA / "typo_progress.json"

BATCH_SIZE = 20
TOTAL = 2456


def batch_list():
    batches = []
    for start in range(1, TOTAL + 1, BATCH_SIZE):
        end = min(start + BATCH_SIZE - 1, TOTAL)
        batches.append([f"{c:04d}" for c in range(start, end + 1)])
    return batches


def load_progress():
    if PROGRESS_FILE.exists():
        return json.loads(PROGRESS_FILE.read_text())
    batches = batch_list()
    return {
        "batches": [
            {"id": i, "chapters": b, "status": "pending"} for i, b in enumerate(batches)
        ]
    }


def save_progress(state):
    PROGRESS_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2))


def cmd_status():
    state = load_progress()
    counts = {}
    for b in state["batches"]:
        counts[b["status"]] = counts.get(b["status"], 0) + 1
    print("批次状态:", dict(sorted(counts.items())))
    print("总批次数:", len(state["batches"]))
    for b in state["batches"]:
        if b["status"] != "done":
            print(
                f"  [{b['id']:3d}] {b['status']:7s} {b['chapters'][0]}~{b['chapters'][-1]}"
            )


def cmd_todo():
    state = load_progress()
    for b in state["batches"]:
        if b["status"] == "pending":
            print(f"{b['id']} {' '.join(b['chapters'])}")


def cmd_mark(batch_id, status):
    state = load_progress()
    for b in state["batches"]:
        if b["id"] == int(batch_id):
            b["status"] = status
            save_progress(state)
            print(f"批次 {batch_id} -> {status}")
            return
    print(f"批次 {batch_id} 不存在", file=sys.stderr)


def cmd_reconcile():
    """对账：chapters 与 typo_candidates 文件一一对应"""
    ch_files = {f.stem for f in CHAPTER_DIR.glob("*.json")}
    cand_files = {f.stem for f in CANDIDATE_DIR.glob("*.json")}
    missing = sorted(ch_files - cand_files)
    extra = sorted(cand_files - ch_files)
    print(f"chapters: {len(ch_files)} 个, candidates: {len(cand_files)} 个")
    if missing:
        print(f"缺失候选: {len(missing)} 个, 如: {missing[:10]}")
    if extra:
        print(f"多余候选: {len(extra)} 个, 如: {extra[:10]}")
    if not missing and not extra:
        print("对账通过: 一一对应")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"
    if cmd == "status":
        cmd_status()
    elif cmd == "todo":
        cmd_todo()
    elif cmd == "mark" and len(sys.argv) == 4:
        cmd_mark(sys.argv[2], sys.argv[3])
    elif cmd == "reconcile":
        cmd_reconcile()
    else:
        print("用法: typo_schedule.py status|todo|reconcile|mark <batch_id> <status>")
