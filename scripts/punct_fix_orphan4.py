#!/usr/bin/env python3
"""punct_fix_orphan4.py - B5 剩余修复: 对话结束右引号写成左引号 (。”→。“)

规则: 栈模拟找未闭合 “; 若其前字符是句末标点(。！？!?)、后 12 字符内
匹配叙述动词(说道/问道/答道/喃喃/低笑/点头等) → 该 “ 改为 ”
(这是对话结束的右引号误写为左引号, 如 “……吧。“韩立问道 → “……吧。”韩立问道)
dry-run 默认, --apply 应用
"""

import json
import re
import sys
from pathlib import Path

DATA = Path(__file__).parent.parent / "data"
CH = DATA / "chapters_fixed"
PREVIEW = DATA / "punct_orphan4_preview.md"

VERB = re.compile(
    r"(说|问|答|喝|叹|笑|摇|点头|摇头|摆手|皱眉|沉思|沉吟|低语|自语|开口|接口|插口|"
    r"询问|解释|介绍|吩咐|叮嘱|喃喃|冷哼|反问|回道|答道|说道|问道|喝道|叹道|笑道)[道着过了的是的]|"
    r"说道|问道|答道|喝道|叹道|笑道|喃喃|开口|冷声|接口|解释|吩咐|叮嘱|反问"
)


def main():
    apply = "--apply" in sys.argv
    total = 0
    lines = [
        f"# 对话结束右引号误写为左引号修复预览({'应用' if apply else 'dry-run'})",
        "",
    ]
    chapters = {}
    for f in sorted(CH.glob("*.json")):
        j = json.loads(f.read_text(encoding="utf-8"))
        txt = j["txt"]
        # 栈模拟: 未闭合 “ 位置
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
            nxt12 = txt[pos + 1 : pos + 13]
            if not VERB.search(nxt12):
                continue
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
