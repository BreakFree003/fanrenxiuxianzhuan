import argparse
import json
import html
import re
from pathlib import Path

from ebooklib import epub

DATA = Path(__file__).parent / "data"
CHAPTER_DIR = DATA / "chapters"
OUTPUT = Path(__file__).parent / "凡人修仙传.epub"

book_info = json.loads((DATA / "book.json").read_text())
chapter_names = json.loads((DATA / "chapters.json").read_text())


def clean_txt(raw: str) -> list[str]:
    raw = raw.replace("\r\n", "\n").replace("\r", "\n")
    paras = [line.strip() for line in raw.split("\n") if line.strip()]
    cleaned = []
    for p in paras:
        if "请收藏本站" in p or "https://" in p:
            continue
        cleaned.append(html.escape(p))
    return cleaned


def build_epub(start: int = 1, end: int = 2456, chapter_dir=None, output=None):
    chapter_dir = Path(chapter_dir) if chapter_dir else CHAPTER_DIR
    output = Path(output) if output else OUTPUT
    book = epub.EpubBook()
    book.set_identifier(f"fanren-xiuxian-{start}-{end}")
    book.set_title(book_info["title"])
    book.set_language("zh-CN")
    book.add_author(book_info["author"])
    book.add_metadata("DC", "description", book_info.get("intro", ""))

    style = "body { font-family: serif; line-height: 1.8; padding: 1em; }"
    css = epub.EpubItem(
        uid="style",
        file_name="style/default.css",
        media_type="text/css",
        content=style,
    )
    book.add_item(css)

    chapters = []
    for cid in range(start, end + 1):
        f = chapter_dir / f"{cid:04d}.json"
        if not f.exists():
            print(f"  SKIP {cid:04d} (not found)")
            continue
        data = json.loads(f.read_text())
        name = data.get("chaptername") or chapter_names[cid - 1]
        paras = clean_txt(data.get("txt", ""))

        content = f"<h1>{html.escape(name)}</h1>\n"
        for p in paras:
            content += f"<p>{p}</p>\n"

        ep_ch = epub.EpubHtml(
            title=name,
            file_name=f"chapter_{cid:04d}.xhtml",
            lang="zh-CN",
        )
        ep_ch.content = (
            f'<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="zh-CN">\n'
            f"<head><title>{html.escape(name)}</title>\n"
            f'<link rel="stylesheet" type="text/css" href="style/default.css"/></head>\n'
            f"<body>{content}</body></html>"
        )
        book.add_item(ep_ch)
        chapters.append(ep_ch)

    book.toc = chapters
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())
    book.spine = ["nav"] + chapters

    epub.write_epub(str(output), book)
    print(f"EPUB written: {output}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", type=int, default=1)
    parser.add_argument("--end", type=int, default=2456)
    parser.add_argument("--chapter-dir", default=None)
    parser.add_argument("--output", default=None)
    args = parser.parse_args()
    build_epub(args.start, args.end, args.chapter_dir, args.output)
