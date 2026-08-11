#!/usr/bin/env python3
"""punct_apply.py - 标点修复应用脚本(dry-run 默认,预览所有修改)

用法:
  python3 scripts/punct_apply.py            # dry-run: 输出全部 before/after 预览
  python3 scripts/punct_apply.py --apply    # 应用修改到 chapters_fixed 并生成快照

规则:
A 连续标点:
  同字符重复(。。，，！！？？、、): 去重保留一个
  ，。 -> 后接关联词(所以/因此/但/但是/也/就/而/却/又/则/还/更/再/并且/而且/不过/然而)时保留逗号,否则保留句号
  。， -> 保留句号
  。、 -> 保留句号
  、。 -> 保留句号
  。！ -> 引号内(后接 ”)保留感叹号,否则保留句号
  ！。 -> 引号内(前有 “)保留感叹号,否则保留句号
  ，； -> 保留逗号(分号前误加逗号,或按 "; ")
  其余两连: 保留后一个标点
  三连及以上: 保留最后一个(按上述规则处理)

B1 对话右引号写成左引号: [。，！？!?]‘ -> 对应 ”
B2 左单右双混用: ‘xxx” -> ‘xxx’
B3 左双右单混用: “xxx’ -> “xxx”
"""

import json
import re
import shutil
import sys
from pathlib import Path

DATA = Path(__file__).parent.parent / "data"
CHAPTER_DIR = DATA / "chapters_fixed"
SNAPSHOT_DIR = DATA / "snapshots"
PREVIEW = DATA / "punct_preview.md"

CONJ = re.compile(
    r"^(所以|因此|但|但是|也|就|而|却|又|则|还|更|再|并且|而且|不过|然而|于是|随后)"
)
PUNCT_RUN = re.compile(r"[，。、；：？！!?]{2,}")

B1_PAT = re.compile(r"[。，！？!?]‘")
# 术语引号内容不含句子标点: 排除 。，！？；： 及 引号字符
TERM_NO = "^‘’“”\n。，！？；：!?、"
B2_PAT = re.compile(rf"‘[{TERM_NO}]{{1,40}}”")
B3_PAT = re.compile(rf"“[{TERM_NO}]{{1,40}}’")


def fix_a_run(run: str, after: str, before_quote: str) -> str:
    """A 类连续标点 -> 保留的标点"""
    if run == "，。":
        return "，" if after and CONJ.match(after) else "。"
    if run == "。，":
        return "。"
    if run == "。、":
        return "。"
    if run == "、。":
        return "。"
    if run == "。！":
        return "！" if after.startswith("”") else "。"
    if run == "！。":
        return "！" if before_quote == "“" else "。"
    if run == "，；":
        return "，"
    # 同字符重复 & 其他: 保留最后一个字符
    return run[-1]


def apply_fixes(txt: str):
    """返回 (new_txt, [(pos, before, after, reason)])"""
    edits = []
    # A 类
    for m in PUNCT_RUN.finditer(txt):
        run = m[0]
        if run == "……" or run.startswith("……") or run == "——":
            continue
        after = txt[m.end() : m.end() + 2]
        before_quote = txt[m.start() - 1] if m.start() > 0 else ""
        keep = fix_a_run(run, after, before_quote)
        if keep != run:
            edits.append((m.start(), run, keep, "A连续标点"))
    # B1: 状态机跟踪 “ 引号配对, 判断每个 [。，！？!?]‘ 是右引号错写还是多余左引号
    in_dq = False
    prev_end = 0
    for m in B1_PAT.finditer(txt):
        p = m.start()
        # 从上一个 B1 点扫描到当前点, 更新引号状态
        seg = txt[prev_end:p]
        for c in seg:
            if c == "“":
                in_dq = True
            elif c == "”":
                in_dq = False
        prev_end = m.start() + 2
        tail = txt[p + 2 : p + 42]
        if "’" in tail:
            continue
        # ‘ 后紧跟 “(左双引号): 如 。‘“嗖”… 应删除 ‘ 而非改 ”
        if tail.startswith("“"):
            edits.append((p, txt[p] + "‘", txt[p], "B1删多余左引号"))
            continue
        # 紧邻术语引号 ‘xxx” (B2 场景, 由 B2 处理): 短串后跟 ”
        if re.match(r"[^。，！？；：、“”‘’]{1,40}”", tail):
            continue
        if in_dq:
            ch = txt[p]
            edits.append((p, ch + "‘", ch + "”", "B1右引号写成左引号"))
        else:
            edits.append((p, txt[p] + "‘", txt[p], "B1删多余左引号"))
    # B2: ‘xxx” -> ‘xxx’
    for m in B2_PAT.finditer(txt):
        p = m.start()
        run = m[0]
        edits.append((p, run, run[:-1] + "’", "B2左单右双混用"))
    # B3: “xxx’ -> “xxx”
    for m in B3_PAT.finditer(txt):
        p = m.start()
        run = m[0]
        edits.append((p, run, run[:-1] + "”", "B3左双右单混用"))

    edits.sort(key=lambda e: e[0], reverse=True)
    new_txt = txt
    for pos, before, after, reason in edits:
        new_txt = new_txt[:pos] + after + new_txt[pos + len(before) :]
    return new_txt, edits


def main():
    apply = "--apply" in sys.argv
    total = 0
    preview_lines = [
        "# 标点修复预览",
        "",
        f"模式: {'应用' if apply else 'dry-run'}",
        "",
    ]
    changed_chapters = 0
    chapter_edits = {}

    for f in sorted(CHAPTER_DIR.glob("*.json")):
        cid = f.stem
        j = json.loads(f.read_text(encoding="utf-8"))
        txt = j.get("txt", "")
        new_txt, edits = apply_fixes(txt)
        if edits:
            changed_chapters += 1
            total += len(edits)
            chapter_edits[cid] = edits
            preview_lines.append(
                f"## {cid} {j.get('chaptername', '')} ({len(edits)} 处)"
            )
            preview_lines.append("")
            for pos, before, after, reason in edits:
                s = max(0, pos - 15)
                e = min(len(txt), pos + len(before) + 15)
                ctx = txt[s:e].replace("\n", "⏎")
                preview_lines.append(f"- [{reason}] `{before}` → `{after}` | …{ctx}…")
            preview_lines.append("")

    preview_lines.insert(2, f"共 {changed_chapters} 章 {total} 处")
    PREVIEW.write_text("\n".join(preview_lines), encoding="utf-8")
    print(f"预览: {changed_chapters} 章 {total} 处 -> {PREVIEW}")

    if apply:
        # 快照
        SNAPSHOT_DIR.mkdir(exist_ok=True)
        snap = SNAPSHOT_DIR / "punct_fix_snapshot"
        if not snap.exists():
            snap.mkdir()
            for f in CHAPTER_DIR.glob("*.json"):
                shutil.copy2(f, snap / f.name)
            print(f"快照已保存: {snap}")
        for f in CHAPTER_DIR.glob("*.json"):
            cid = f.stem
            if cid not in chapter_edits:
                continue
            j = json.loads(f.read_text(encoding="utf-8"))
            txt = j["txt"]
            new_txt, _ = apply_fixes(txt)
            j["txt"] = new_txt
            f.write_text(json.dumps(j, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"已应用: {len(chapter_edits)} 章")


if __name__ == "__main__":
    main()
