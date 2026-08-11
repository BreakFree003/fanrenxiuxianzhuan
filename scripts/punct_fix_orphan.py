#!/usr/bin/env python3
"""punct_fix_orphan.py - 批量修复孤立右引号两类问题(仅这两类,精确替换)

1. 段首 ” -> “ : 换行符后紧跟 ” 且 该 ” 为孤立(深度0时出现), 改为 “
2. 反引号对 ”xxx“ -> “xxx” : ” 后紧跟汉字串(不含标点/引号)到 “ 结束, 整体反转

其他孤立 ”(464 处存疑)不在此脚本内。

应用前按位置去重(同位置命中两类时保留覆盖更长的编辑), 防止 ”xxx“ -> “xxx”“ 复制损坏。
dry-run 默认, --apply 应用。
"""

import json
import re
import sys
from pathlib import Path

DATA = Path(__file__).parent.parent / "data"
CH = DATA / "chapters_fixed"

TERM = re.compile(r"”[^”^“。，！？；：、！?\n]{1,15}“")


def main():
    apply = "--apply" in sys.argv
    # 收集修改
    changes = []  # (file, [(before, after)])
    for f in sorted(CH.glob("*.json")):
        j = json.loads(f.read_text(encoding="utf-8"))
        txt = j["txt"]
        depth = 0
        edits = []
        # 记录每个孤立 ” 的位置(深度0)
        orphan_pos = set()
        for i, c in enumerate(txt):
            if c == "“":
                depth += 1
            elif c == "”":
                if depth == 0:
                    orphan_pos.add(i)
                else:
                    depth -= 1
        # 1. 段首 ”: 孤立且前面是换行
        for i in sorted(orphan_pos):
            if i > 0 and txt[i - 1] == "\n":
                edits.append((i, "”", "“", "段首右引号"))
        # 2. 反引号对: 孤立 ” 且匹配 ”xxx“ 模式
        for i in sorted(orphan_pos):
            m = TERM.match(txt, i)
            if m:
                seg = m.group()
                edits.append((i, seg, "“" + seg[1:-1] + "”", "反引号对"))
        if edits:
            changes.append((f, edits))

    # 汇总
    c1 = sum(1 for _, es in changes for e in es if e[3] == "段首右引号")
    c2 = sum(1 for _, es in changes for e in es if e[3] == "反引号对")
    print(
        f"段首右引号: {c1} 处 | 反引号对: {c2} 处 | 共 {c1 + c2} 处, {len(changes)} 章"
    )
    if not apply:
        print("dry-run, 未写入。确认无误后使用 --apply 应用")
        return

    # 应用(按位置一次替换, 避免同一文件多处编辑相互偏移)
    for f, es in changes:
        j = json.loads(f.read_text(encoding="utf-8"))
        txt = j["txt"]
        # 同位置去重: 段首 ” 与 反引号对 ”xxx“ 可能在同一位置命中
        # (段首 ” 恰为反引号对首字符)。保留 before 更长(覆盖更全)的编辑,
        # 避免两个替换叠加造成 ”xxx“ -> “xxx”“ 复制型损坏。
        best = {}
        for pos, before, after, kind in es:
            if pos not in best or len(before) > len(best[pos][0]):
                best[pos] = (before, after)
        es = [
            (pos, before, after, "")
            for pos, (before, after) in sorted(
                best.items(), key=lambda kv: kv[0], reverse=True
            )
        ]
        # 按位置从后往前应用
        parts = []
        last = len(txt)
        for pos, before, after, _ in es:
            end = pos + len(before)
            assert txt[pos:end] == before, f"{f} 位置不匹配: {txt[pos:end]} != {before}"
            parts.append(txt[end:last])
            parts.append(after)
            last = pos
        parts.append(txt[:last])
        new_txt = "".join(reversed(parts))
        j["txt"] = new_txt
        f.write_text(json.dumps(j, ensure_ascii=False, indent=2), encoding="utf-8")
    print("已应用")


if __name__ == "__main__":
    main()
