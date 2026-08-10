#!/usr/bin/env python3
"""build_txt.py - 从章节目录拼接纯文本（与原 txt 格式一致）

格式：文件头 2 空行；每章 = 标题行 + 空行 + 正文段落（\n 分隔）；章间 1 空行。
用法: build_txt.py [--chapters-dir data/chapters_fixed] [--output 凡人修仙传v2.txt]
"""

import argparse
import json
from pathlib import Path

DATA = Path(__file__).parent.parent / "data"


def build(chapter_dir: Path, output: Path, start: int = 1, end: int = 2456):
    parts = ["\n\n"]
    for cid in range(start, end + 1):
        f = chapter_dir / f"{cid:04d}.json"
        if not f.exists():
            print(f"SKIP {cid:04d}")
            continue
        data = json.loads(f.read_text())
        title = data.get("chaptername") or ""
        txt = data.get("txt", "")
        parts.append(f"{title}\n\n{txt}\n\n")
    output.write_text("".join(parts), encoding="utf-8")
    lines = output.read_text(encoding="utf-8").count("\n")
    print(f"TXT written: {output} ({lines} 行)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--chapters-dir", default=str(DATA / "chapters"))
    parser.add_argument(
        "--output", default=str(Path(__file__).parent.parent / "凡人修仙传v2.txt")
    )
    parser.add_argument("--start", type=int, default=1)
    parser.add_argument("--end", type=int, default=2456)
    args = parser.parse_args()
    build(Path(args.chapters_dir), Path(args.output), args.start, args.end)
