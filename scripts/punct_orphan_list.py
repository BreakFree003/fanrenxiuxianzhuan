#!/usr/bin/env python3
"""punct_orphan_list.py - 生成剩余孤立 ” 完整清单(只读)"""

import json
import re
from pathlib import Path

DATA = Path(__file__).parent.parent / "data"
CH = DATA / "chapters_fixed"
OUT = DATA / "punct_orphan_remaining.md"

TERM = re.compile(r"”[^”^“。，！？；：、！?\n]{1,15}“")


def main():
    lines = ["# 剩余孤立右引号 ” 清单(需人工甄别)", ""]
    stats = {"句末后": 0, "文字后": 0, "反引号对未匹配": 0, "其他": 0}
    total = 0
    for f in sorted(CH.glob("*.json")):
        j = json.loads(f.read_text(encoding="utf-8"))
        txt = j["txt"]
        depth = 0
        items = []
        for i, c in enumerate(txt):
            if c == "“":
                depth += 1
            elif c == "”":
                if depth == 0:
                    prev = txt[i - 1] if i > 0 else ""
                    after = txt[i + 1] if i + 1 < len(txt) else ""
                    if after and not after.startswith("\n") and TERM.match(txt, i):
                        cat = "反引号对未匹配"
                    elif i > 0 and txt[i - 1] == "\n":
                        cat = "段首"
                    elif prev in "。！？!?":
                        cat = "句末后"
                    elif re.match(r"[\u4e00-\u9fff]", prev):
                        cat = "文字后"
                    else:
                        cat = "其他"
                    stats[cat] = stats.get(cat, 0) + 1
                    total += 1
                    ctx = txt[max(0, i - 20) : i + 20].replace("\n", "⏎")
                    items.append((i, cat, ctx))
                else:
                    depth -= 1
        if items:
            lines.append(f"## {f.stem} {j.get('chaptername', '')}")
            for i, cat, ctx in items:
                lines.append(f"- [{cat}] …{ctx}…")
            lines.append("")
    lines.insert(2, f"共 {total} 处")
    lines.insert(3, f"分类: {json.dumps(stats, ensure_ascii=False)}")
    OUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"共 {total} 处 -> {OUT}")
    print(stats)


if __name__ == "__main__":
    main()
