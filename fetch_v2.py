import json
import time
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

DATA = Path(__file__).parent / "data"
CHAPTER_DIR = DATA / "chapters"
CHAPTER_DIR.mkdir(parents=True, exist_ok=True)

REF = json.loads((DATA / "txt_ref.json").read_text(encoding="utf-8"))

POLLUTION_MARKERS = ["大学阿拉伯语", "我今年２２岁"]

book_info = json.loads((DATA / "book.json").read_text())
chapter_names = json.loads((DATA / "chapters.json").read_text())

START = int(sys.argv[1]) if len(sys.argv) > 1 else 1
END = int(sys.argv[2]) if len(sys.argv) > 2 else 2456

DELAY = 0.8
ERROR_DELAY = 2.0


def is_clean(data: dict) -> bool:
    txt = data.get("txt", "")
    for m in POLLUTION_MARKERS:
        if m in txt[:500]:
            return False
    chinese_count = sum(1 for c in txt[:500] if "\u4e00" <= c <= "\u9fff")
    return chinese_count >= 50


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 800},
        )
        page = ctx.new_page()
        page.goto("https://www.bqg107.xyz/#/book/546/", wait_until="domcontentloaded")
        time.sleep(3)

        total = END - START + 1
        for i, cid in enumerate(range(START, END + 1), 1):
            out = CHAPTER_DIR / f"{cid:04d}.json"

            # Skip if already exists and is clean
            if out.exists():
                existing = json.loads(out.read_text())
                if is_clean(existing) and len(existing.get("txt", "")) > 200:
                    print(f"  [{cid}/{END}] SKIP (cached & clean)")
                    continue

            name = chapter_names[cid - 1] if cid <= len(chapter_names) else f"第{cid}章"
            print(f"  [{cid}/{END}] {name} ...", end=" ", flush=True)

            saved = False
            for attempt in range(8):
                try:
                    # Strategy A: normal fetch
                    data = page.evaluate(f"""
                        () => fetch(get_api('chapter', {{id: 546, chapterid: {cid}}}))
                            .then(r => r.json())
                    """)

                    if is_clean(data):
                        out.write_text(json.dumps(data, ensure_ascii=False, indent=2))
                        print(f"OK ({len(data['txt'])} chars, normal)")
                        saved = True
                        break

                    # Strategy B: chapter_error fallback
                    error_data = page.evaluate(f"""
                        () => $.ajax({{
                            url: '/api/action',
                            method: 'POST',
                            data: {{
                                action: 'chapter_error',
                                bookid: {data["dirid"]},
                                chapterid: {cid},
                                chaptername: '{data["chaptername"]}',
                                time: {data["time"]}
                            }},
                            dataType: 'json'
                        }})
                    """)

                    if error_data.get("txt"):
                        corrected = dict(data)
                        corrected["txt"] = error_data["txt"]
                        corrected["_via"] = "chapter_error"
                        if is_clean(corrected):
                            out.write_text(
                                json.dumps(corrected, ensure_ascii=False, indent=2)
                            )
                            print(f"OK ({len(corrected['txt'])} chars, error_report)")
                            saved = True
                            break

                    # Strategy C: wait and retry
                    if attempt < 3:
                        time.sleep(2.0)
                    else:
                        time.sleep(5.0)

                except Exception as e:
                    if attempt < 3:
                        time.sleep(3.0)

            if not saved:
                print(f"FAILED after 8 attempts")

            time.sleep(DELAY)

        browser.close()


if __name__ == "__main__":
    main()
