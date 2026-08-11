#!/usr/bin/env python3
"""punct_fix_orphan2.py - 修复剩余孤立 ”(372 处)

规则:
1. 候选改“: 孤立 ” 且 后一字符为文字(非换行非“), 且 后续文本中还存在另一个 ”
   (即它其实是缺失左引号的引语, 前面的 ” 应为 “)
2. 删”: 非候选的孤立 ” (段首/后接换行/后80无配对 → 叙述结束的冗余右引号)

应用方式: 将候选视为 “ 重新扫描配对, 未配对的孤立 ” 删除
dry-run 默认, --apply 应用
"""

import json
import re
import sys
from pathlib import Path

DATA = Path(__file__).parent.parent / "data"
CH = DATA / "chapters_fixed"
PREVIEW = DATA / "punct_orphan2_preview.md"


def analyze(txt):
    """返回 (改“的pos列表, 删”的pos列表, 补“的pos列表[在pos前补])"""
    # 第一遍: 找孤立 ”(深度0)
    depth = 0
    orphans = []
    for i, c in enumerate(txt):
        if c == "“":
            depth += 1
        elif c == "”":
            if depth == 0:
                orphans.append(i)
            else:
                depth -= 1
    orphan_set = set(orphans)
    keep = set()  # 术语成对中的第二个 ”: 保留
    protect = set()  # 拟声词右引号(前已补“): 独立保留, 不参与配对
    change = set()  # ” -> “
    delete = set()  # 删 ”
    insert = set()  # 在该位置前补 “ (拟声词缺左引号)
    # 术语成对检测: ”汉字{1,15}” 且 前一个字符不是句末标点/右引号
    # (第一个 ” 是左引号错写, 第二个 ” 保留) — 不依赖孤儿判定, 全文匹配
    term_pat = re.compile(r"”[\u4e00-\u9fff]{1,15}”")
    for m in term_pat.finditer(txt):
        a, b = m.start(), m.end() - 1
        prevc = txt[a - 1] if a > 0 else ""
        if prevc and prevc not in "。！？!?“”":
            change.add(a)
            keep.add(b)
    # 剩余孤立: 逐类判断
    verb_pat = re.compile(
        r"(说|问|答|喝|叹|笑|摇|点头|摇头|摆手|皱眉|沉思|沉吟)[道着过了]|"
        r"说道|问道|答道|喝道|叹道|笑道|喃喃|开口|冷声|接口|解释"
    )
    for i in orphans:
        if i in change or i in keep or i in delete:
            continue
        nxt = txt[i + 1] if i + 1 < len(txt) else ""
        prev = txt[i - 1] if i > 0 else ""
        # 句末标点后的重叠 ”” : 第一个 ” 是前句冗余右引号(删),
        # 第二个 ” 是下句引语左引号错写(后接动词→删, 否则→改 “)
        if prev in "。！？!?" and nxt == "”" and (i + 1) in orphan_set:
            delete.add(i)
            if verb_pat.search(txt[i + 2 : i + 14]):
                delete.add(i + 1)
            else:
                change.add(i + 1)
            continue
        # 后接换行/“(→ 冗余右引号, 待第二遍(可能配对前面改的“), 不标记
        # 拟声词缺左引号: 前是汉字(或叠词), 后接 的/一/两/几/声/下/…(短虚词),
        # 且 前二字符不是句末标点/右引号(否则是 。”噗” → 应改“ 而非补)
        # 补“ 在拟声词开头前: 单字(嗖” → “嗖”)或叠词(噗噗” → “噗噗”)
        if (
            re.match(r"[\u4e00-\u9fff]", prev)
            and re.match(r"[的一两几声下]", nxt)
            and (i < 2 or txt[i - 2] not in "。！？!?”")
        ):
            start = i
            while (
                start > 0
                and txt[start - 1] == prev
                and re.match(r"[\u4e00-\u9fff]", txt[start - 1])
            ):
                start -= 1
            insert.add(start - 1)  # 在拟声词开头前补 “
            protect.add(i)  # 拟声词右引号保留
            continue
        # 前二字符是孤立 ”(。”噗” 模式): 前一个 ” 改 “, 当前 ” 保留
        if (
            i >= 2
            and txt[i - 2] == "”"
            and (i - 2) in orphan_set
            and re.match(r"[\u4e00-\u9fff]", prev)
            and re.match(r"[的一两几声下]", nxt)
        ):
            change.add(i - 2)
            protect.add(i)
            continue
        # 重叠 ”” : 后接叙述动词 → 删; 否则是下一句引语开始 → 改 “
        if prev == "”":
            if verb_pat.search(txt[i + 1 : i + 12]):
                delete.add(i)
            else:
                change.add(i)
            continue
        # 后接叙述动词(某人说道/叹了等) → 待配对(可能配对前面改的“), 留待第二遍
        if verb_pat.search(txt[i + 1 : i + 12]):
            continue  # 不标记, 第二遍栈模拟: 栈非空配对保留, 栈空删
        # 段首 ” (段落开头): 新对话/引语开始 → 改 “
        if i == 0 or txt[i - 1] == "\n":
            if nxt and not nxt.startswith("\n"):
                change.add(i)
            continue
        # 引语/术语左引号错写: 前是汉字、句末标点或冒号(对话前); 后接换行/“(不在此列, 留第二遍)
        if (
            (re.match(r"[\u4e00-\u9fff]", prev) or prev in "。！？!?：" or prev == "：")
            and nxt
            and not nxt.startswith("\n")
            and nxt != "“"
        ):
            change.add(i)
            continue
        # 其他: 不标记, 留待第二遍栈模拟(栈非空配对, 栈空删)
    # 第二遍: 配对模拟。change 视为 “; 相邻 change 配对(前改“后保留);
    # 遇到普通 ”(含未标记的孤立”) 出栈配对, 栈空则删; 章末栈中剩余 change → 转删
    stack = []
    to_delete2 = set()
    for i, c in enumerate(txt):
        if c == "“":
            stack.append((i, False))
        elif i in change:
            if stack and stack[-1][1]:
                stack.pop()  # 前一 change 改 “, 当前保留 ”
                change.discard(i)
                keep.add(i)
            else:
                stack.append((i, True))
        elif c == "”":
            if i in protect:
                continue  # 拟声词右引号(前已补“), 独立保留
            if stack:
                stack.pop()
            else:
                to_delete2.add(i)
    for pos, is_cand in stack:
        if is_cand:
            change.discard(pos)
            delete.add(pos)
    delete |= to_delete2
    # 应用顺序优先级: 同一位置若同时被标记, 优先 change > insert > delete
    overlap = change & delete & insert
    change -= overlap
    delete -= overlap
    insert -= overlap
    return change, delete, insert


def main():
    apply = "--apply" in sys.argv
    total_c, total_d, total_i = 0, 0, 0
    lines = [f"# 孤立右引号修复预览({'应用' if apply else 'dry-run'})", ""]
    chapters = {}
    for f in sorted(CH.glob("*.json")):
        j = json.loads(f.read_text(encoding="utf-8"))
        txt = j["txt"]
        change, dele, insert = analyze(txt)
        if not change and not dele and not insert:
            continue
        chapters[f] = (change, dele, insert)
        total_c += len(change)
        total_d += len(dele)
        total_i += len(insert)
        lines.append(f"## {f.stem} {j.get('chaptername', '')}")
        for i in sorted(change):
            ctx = txt[max(0, i - 15) : i + 15].replace("\n", "⏎")
            lines.append(f"- [改“] …{ctx}…")
        for i in sorted(dele):
            ctx = txt[max(0, i - 15) : i + 15].replace("\n", "⏎")
            lines.append(f"- [删”] …{ctx}…")
        for i in sorted(insert):
            ctx = txt[max(0, i - 15) : i + 15].replace("\n", "⏎")
            lines.append(f"- [补“] …{ctx}…")
        lines.append("")
    lines.insert(
        2, f"共 改“ {total_c} | 删” {total_d} | 补“ {total_i} | {len(chapters)} 章"
    )
    PREVIEW.write_text("\n".join(lines), encoding="utf-8")
    print(
        f"预览: 改“ {total_c} | 删” {total_d} | 补“ {total_i} | {len(chapters)} 章 -> {PREVIEW}"
    )
    if not apply:
        return
    for f, (change, dele, insert) in chapters.items():
        j = json.loads(f.read_text(encoding="utf-8"))
        txt = j["txt"]
        # 按位置从后往前: 补 = 在 ” 前插入 “; 改 = ” -> “; 删 = 移除 ”
        edits = []
        for i in change:
            edits.append((i, "“"))
        for i in insert:
            edits.append((i, "“" + txt[i]))
        for i in dele:
            edits.append((i, ""))
        # 同位置冲突处理: 优先 补(插引号), 再 改
        by_pos = {}
        for i, repl in edits:
            by_pos[i] = repl if repl else by_pos.get(i, "")
        parts = []
        last = len(txt)
        for pos in sorted(by_pos, reverse=True):
            repl = by_pos[pos]
            parts.append(txt[pos + 1 : last] if pos + 1 <= last else "")
            parts.append(repl)
            last = pos
        parts.append(txt[:last])
        new_txt = "".join(reversed(parts))
        j["txt"] = new_txt
        f.write_text(json.dumps(j, ensure_ascii=False, indent=2), encoding="utf-8")
    print("已应用")


if __name__ == "__main__":
    main()
