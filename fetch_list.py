import httpx
import json
from pathlib import Path

DATA = Path(__file__).parent / "data"
DATA.mkdir(parents=True, exist_ok=True)

BASE = "https://www.bqg107.xyz"
BOOK_ID = "546"

client = httpx.Client(
    headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Referer": f"{BASE}/",
    }
)

# 书信息
r = client.get(f"{BASE}/api/book?id={BOOK_ID}")
r.raise_for_status()
book = r.json()
(DATA / "book.json").write_text(json.dumps(book, ensure_ascii=False, indent=2))
print(f"Book: {book['title']} by {book['author']}, {book['lastchapterid']} chapters")

# 章节列表
r = client.get(f"{BASE}/api/booklist?id={BOOK_ID}")
r.raise_for_status()
chapters = r.json()["list"]
(DATA / "chapters.json").write_text(json.dumps(chapters, ensure_ascii=False, indent=2))
print(f"Chapter list: {len(chapters)} chapters fetched")
