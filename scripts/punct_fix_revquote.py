#!/usr/bin/env python3
"""punct_fix_revquote.py - 修复反引号对: “xxx“ (第二个 “ 应为 ”)

规则: 匹配 “[^“”\n]{1,20}“ 且 第二个 “ 后 15 字符内无 ”(无嵌套引用)
→ 第二个 “ 改为 ”
dry-run 默认, --apply 应用
"""

import json
import re
import sys
from pathlib import Path

DATA = Path(__file__).parent.parent / "data"
CH = DATA / "chapters_fixed"
PREVIEW = DATA / "punct_revquote_preview.md"

PAT = re.compile(r"“[^“”\n]{1,20}“")


def main():
    apply = "--apply" in sys.argv
    total = 0
    lines = [f"# 反引号对修复预览({'应用' if apply else 'dry-run'})", ""]
    chapters = {}
    for f in sorted(CH.glob("*.json")):
        j = json.loads(f.read_text(encoding="utf-8"))
        txt = j["txt"]
        edits = []
        for m in PAT.finditer(txt):
            a, b = m.start(), m.end() - 1
            after = txt[b + 1 : b + 16]
            if "”" in after:
                continue  # 窗口内有右引号, 可能为嵌套引用, 保守跳过
            edits.append(b)  # 第二个 “ -> ”
        if edits:
            chapters[f] = edits
            total += len(edits)
            lines.append(f"## {f.stem} {j.get('chaptername', '')}")
            for b in edits:
                ctx = txt[max(0, b - 12) : b + 12].replace("\n", "⏎")
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
        for b in edits:
            assert chars[b] == "“", f"{f} 位置 {b} 不是左引号"
            chars[b] = "”"
        j["txt"] = "".join(chars)
        f.write_text(json.dumps(j, ensure_ascii=False, indent=2), encoding="utf-8")
    print("已应用")


if __name__ == "__main__":
    main()
