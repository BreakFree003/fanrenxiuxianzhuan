#!/usr/bin/env python3
"""punct_fix9.py - 一次性人工修复 9 处特殊引号案例(精确匹配,次数校验)

逐条说明:
- 1043: 对话左单引号应为左双引号: ‘叫本妃 -> “叫本妃
- 1055: 嵌套引号缺内层右单引号: 不行！” -> 不行！’”
- 1614: 术语引号缺右单引号: ‘辟雷伞的人 -> ‘辟雷伞’的人
- 2131: 术语引号右半写成左引号: ‘韩前辈‘ -> ‘韩前辈’
- 2163: 术语引号左半写成右单引号: 发动’颠倒 -> 发动‘颠倒
- 0500: 术语引号右半写成左双引号: ‘天星令“ -> ‘天星令’
- 2034: 竞拍价右引号写成左单引号: “六百万‘ -> “六百万”
- 2195: 对话结束错写: 。‘” -> 。” + “(先于自动规则执行)
"""

import json
from pathlib import Path

DATA = Path(__file__).parent.parent / "data"
CH = DATA / "chapters_fixed"

FIXES = [
    ("1043", "好说话了。”\n‘叫本妃出来做什么", "好说话了。”\n“叫本妃出来做什么"),
    ("1055", "“‘叱念真雷，这绝对不行！”", "“‘叱念真雷，这绝对不行！’”"),
    ("1614", "申请‘辟雷伞的人", "申请‘辟雷伞’的人"),
    ("2131", "这位‘韩前辈‘，", "这位‘韩前辈’，"),
    ("2163", "你马上发动’颠倒换形五岳禁制’", "你马上发动‘颠倒换形五岳禁制’"),
    ("0500", "发出了‘天星令“。", "发出了‘天星令’。"),
    ("2034", "“六百万‘", "“六百万”"),
    ("2195", "是势在必得了。‘”那我们", "是势在必得了。”\u201c那我们"),
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
