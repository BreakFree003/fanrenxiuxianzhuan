#!/usr/bin/env python3
"""punct_fix5.py - 一次性人工修复 5 处单引号不平案例(精确匹配,次数校验)"""

import json
from pathlib import Path

DATA = Path(__file__).parent.parent / "data"
CH = DATA / "chapters_fixed"

FIXES = [
    ("0407", "“咦‘极阴老祖微露出一点讶色！", "“咦！”极阴老祖微露出一点讶色！"),
    ("0524", "结果‘扑哧“一声响后", "结果“扑哧”一声响后"),
    ("0565", "又说道：\n‘当年我和妍丽师姐", "又说道：\n“当年我和妍丽师姐"),
    ("0929", "又如此的说道’。", "又如此的说道。"),
    ("0957", "对所谓的“掌天印‘更是一点不知", "对所谓的“掌天印”更是一点不知"),
]

for cid, before, after in FIXES:
    f = CH / f"{cid}.json"
    j = json.loads(f.read_text(encoding="utf-8"))
    txt = j["txt"]
    n = txt.count(before)
    if n != 1:
        print(f"[{cid}] 跳过: 匹配 {n} 次 (期望 1): {before[:40]}")
        continue
    j["txt"] = txt.replace(before, after)
    f.write_text(json.dumps(j, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[{cid}] 已修复: {before[:40]} -> {after[:40]}")
