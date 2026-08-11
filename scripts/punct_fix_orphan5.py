#!/usr/bin/env python3
"""punct_fix_orphan5.py - B5 剩余修复第二轮: 对话结束右引号误写为左引号

规则: 栈模拟找未闭合 “; 若其前字符是句末标点(。！？!?)、且 后 20 字符内
无 ”(无配对, 即不是嵌套) → 该 “ 改为 ”
(对话结束的右引号误写为左引号, 如 “……吧。“韩立目光一闪 → “……吧。”韩立目光一闪)
dry-run 默认, --apply 应用
"""

import json
import sys
from pathlib import Path

DATA = Path(__file__).parent.parent / "data"
CH = DATA / "chapters_fixed"
PREVIEW = DATA / "punct_orphan5_preview.md"


def main():
    apply = "--apply" in sys.argv
    total = 0
    lines = [
        f"# 对话结束右引号误写为左引号修复预览-2({'应用' if apply else 'dry-run'})",
        "",
    ]
    chapters = {}
    for f in sorted(CH.glob("*.json")):
        j = json.loads(f.read_text(encoding="utf-8"))
        txt = j["txt"]
        stack = []
        for i, c in enumerate(txt):
            if c == "“":
                stack.append(i)
            elif c == "”":
                if stack:
                    stack.pop()
        edits = []
        for pos in stack:
            if pos == 0:
                continue
            prev = txt[pos - 1]
            if prev not in "。！？!?":
                continue
            if "”" in txt[pos + 1 : pos + 21]:
                continue  # 后 20 字符内有 ”(嵌套/配对) → 不改
            edits.append(pos)
        if edits:
            chapters[f] = edits
            total += len(edits)
            lines.append(f"## {f.stem} {j.get('chaptername', '')}")
            for pos in edits:
                ctx = txt[max(0, pos - 18) : pos + 18].replace("\n", "⏎")
                lines.append(f"- [改”] …{ctx}…")
            lines.append("")
    lines.insert(2, f"共 {total} 处, {len(chapters)} 章")
    PREVIEW.write_text("\n".join(lines), encoding="utf-8")
    print(f"预览: {total} 处, {len(chapters)} 章 -> {PREVIEW}")
    if not apply:
        return
    for f, edits in chapters.items():
        j = json.loads(f.read_text(encoding="utf-8"))
        txt = j["txt"]
        chars = list(txt)
        for pos in edits:
            assert chars[pos] == "“", f"{f} 位置 {pos} 不是左引号"
            chars[pos] = "”"
        j["txt"] = "".join(chars)
        f.write_text(json.dumps(j, ensure_ascii=False, indent=2), encoding="utf-8")
    print("已应用")


if __name__ == "__main__":
    main()
