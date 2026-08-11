#!/usr/bin/env python3
"""punct_fix8.py - 一次性人工修复 8 处 B4 缺引号/错位(仅指定位置,精确匹配,次数校验)"""

import json
from pathlib import Path

DATA = Path(__file__).parent.parent / "data"
CH = DATA / "chapters_fixed"

# (章节, 匹配串, 替换串)
FIXES = [
    ("0707", "对这‘紫铖兜好像", "对这‘紫铖兜’好像"),
    ("0842", "“咦！”‘南陇侯有些意外", "“咦！”‘南陇侯’有些意外"),
    ("0842", "南陇侯’见此", "‘南陇侯’见此"),
    ("0842", "‘南陇侯满是黑气", "‘南陇侯’满是黑气"),
    ("0844", "‘南陇侯一见身前", "‘南陇侯’一见身前"),
    ("1823", "的‘移海扇，足可", "的‘移海扇’，足可"),
    ("2116", "，‘烁金河谷‘中", "，‘烁金河谷’中"),
    ("2402", "有关“绝世凶魔‘在", "有关“绝世凶魔”在"),
    ("1587", "又接着说道：\n‘那些圣族", "又接着说道：\n“那些圣族"),
]

for cid, before, after in FIXES:
    f = CH / f"{cid}.json"
    j = json.loads(f.read_text(encoding="utf-8"))
    txt = j["txt"]
    n = txt.count(before)
    if n != 1:
        print(f"[{cid}] 跳过: 匹配 {n} 次 (期望 1): {before[:30]}")
        continue
    j["txt"] = txt.replace(before, after)
    f.write_text(json.dumps(j, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[{cid}] 已修复: {before[:40]} -> {after[:40]}")
