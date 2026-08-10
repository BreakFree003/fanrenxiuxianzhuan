#!/usr/bin/env python3
"""snapshot_verify.py - 哈希快照生成与比对

用法:
  snapshot_verify.py make <path.json>   生成快照
  snapshot_verify.py check <path.json>  比对当前文件与快照，输出差异
"""

import hashlib
import json
import sys
from pathlib import Path

PROTECTED = [
    ("data/chapters", "*.json"),
    ("凡人修仙传.txt", None),
    ("凡人修仙传.epub", None),
    ("凡人修仙传.mobi", None),
    ("凡人修仙传.pdf", None),
]


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def collect() -> dict:
    snap = {}
    for target, pattern in PROTECTED:
        p = Path(target)
        if p.is_dir():
            for f in sorted(p.glob(pattern)):
                snap[f"{target}/{f.name}"] = sha256_file(f)
        elif p.exists():
            snap[target] = sha256_file(p)
    return snap


def cmd_make(path):
    snap = {"generated_at": __import__("time").time(), "files": collect()}
    Path(path).write_text(json.dumps(snap, indent=2))
    print(f"快照 {len(snap['files'])} 个文件 -> {path}")


def cmd_check(path):
    if not Path(path).exists():
        print(f"快照文件不存在: {path}", file=sys.stderr)
        sys.exit(1)
    baseline = json.loads(Path(path).read_text())["files"]
    current = collect()
    changed = [k for k in baseline if baseline[k] != current.get(k)]
    removed = [k for k in baseline if k not in current]
    added = [k for k in current if k not in baseline]
    if not changed and not removed and not added:
        print("比对通过: 全部受保护文件未被改动")
    else:
        for k in changed:
            print(f"已改动: {k}")
        for k in removed:
            print(f"已删除: {k}")
        for k in added:
            print(f"新增(受保护路径): {k}")
        sys.exit(1)


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("用法: snapshot_verify.py make|check <path.json>")
        sys.exit(1)
    cmd, path = sys.argv[1], sys.argv[2]
    if cmd == "make":
        cmd_make(path)
    elif cmd == "check":
        cmd_check(path)
    else:
        print("未知命令", file=sys.stderr)
        sys.exit(1)
