import json
import time
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

DATA = Path(__file__).parent / "data"
CHAPTER_DIR = DATA / "chapters"
CHAPTER_DIR.mkdir(parents=True, exist_ok=True)

BASE_URL = "https://www.bqg107.xyz/#/"
BOOK_ID = 546

START = int(sys.argv[1]) if len(sys.argv) > 1 else 1
END = int(sys.argv[2]) if len(sys.argv) > 2 else 50
DELAY = float(sys.argv[3]) if len(sys.argv) > 3 else 0.5

chapter_names = json.loads((DATA / "chapters.json").read_text())


def fetch_chapter(page, chapter_id: int):
    resp = page.evaluate(f"""
        () => {{
            const url = get_api('chapter', {{id: {BOOK_ID}, chapterid: {chapter_id}}});
            return fetch(url).then(r => {{
                if (!r.ok) throw new Error('HTTP ' + r.status);
                return r.json();
            }});
        }}
    """)
    return resp


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36"
        )
        page = ctx.new_page()
        page.goto(BASE_URL, wait_until="domcontentloaded")
        time.sleep(2)

        total = END - START + 1
        for i, cid in enumerate(range(START, END + 1), 1):
            out = CHAPTER_DIR / f"{cid:04d}.json"
            if out.exists():
                print(f"  [{cid}] SKIP (exists)")
                continue

            name = chapter_names[cid - 1] if cid <= len(chapter_names) else f"第{cid}章"
            print(f"  [{cid}/{END}] {name} ...", end=" ", flush=True)

            for attempt in range(3):
                try:
                    data = fetch_chapter(page, cid)
                    if not data or "txt" not in data:
                        raise ValueError(f"Unexpected response: {data}")
                    out.write_text(json.dumps(data, ensure_ascii=False, indent=2))
                    print(f"OK ({len(data['txt'])} chars)")
                    break
                except Exception as e:
                    print(f"FAIL attempt {attempt + 1}: {e}")
                    time.sleep(2)
            else:
                print(f"  [{cid}] GAVE UP after 3 attempts")

            time.sleep(DELAY)

        browser.close()


if __name__ == "__main__":
    main()
