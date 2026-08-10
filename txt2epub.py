import re
import html
from pathlib import Path

from ebooklib import epub

TXT = Path("/tmp/fanren.txt")
OUTPUT = Path(__file__).parent / "凡人修仙传.epub"

raw = TXT.read_bytes()
txt = raw.decode("gbk")

# Remove the header banner
header_end = txt.find("内容简介：")
if header_end > 0:
    txt = txt[header_end:]

# Remove the footer banner
footer_pos = txt.rfind("==========================================================")
if footer_pos > 0:
    txt = txt[:footer_pos].rstrip()

# Split into chapters (including extras)
ch_pattern = re.compile(
    r"^(第[零一二两三四五六七八九十百千万亿\d]+[章节篇]\s*\S*|感言|凡人外传[·\s]*仙界篇[·\s]*[一二三四五六七八九十\d]*|凡人外传)",
    re.MULTILINE,
)
splits = list(ch_pattern.finditer(txt))

chapters_data = []
for i, m in enumerate(splits):
    name = m.group(0).strip()
    start = m.start()
    end = splits[i + 1].start() if i + 1 < len(splits) else len(txt)
    body = txt[m.end() : end].strip()
    chapters_data.append((name, body))

# Separate main story from extras
main_end = len(chapters_data)
for i, (name, _) in enumerate(chapters_data):
    if name.strip() in ("感言",) or name.strip().startswith("凡人外传"):
        main_end = i
        break

main_chapters = chapters_data[:main_end]
extras = chapters_data[main_end:]

print(f"Main chapters: {len(main_chapters)}")
print(f"First: {main_chapters[0][0]}")
print(f"Last: {main_chapters[-1][0]}")
print(f"Extras: {len(extras)}")
for n, _ in extras:
    print(f"  {n}")


def build_epub():
    book = epub.EpubBook()
    book.set_identifier("fanren-xiuxian-quanben")
    book.set_title("凡人修仙传")
    book.set_language("zh-CN")
    book.add_author("忘语")
    book.add_metadata(
        "DC",
        "description",
        "一个普通山村小子，偶然下进入到当地江湖小门派，成了一名记名弟子。他以这样身份，如何在门派中立足，如何以平庸的资质进入到修仙者的行列，从而笑傲三界之中！",
    )

    style = "body { font-family: serif; line-height: 1.8; padding: 1em; text-indent: 2em; } p { margin: 0.3em 0; } h1 { text-align: center; text-indent: 0; }"
    css = epub.EpubItem(
        uid="style",
        file_name="style/default.css",
        media_type="text/css",
        content=style,
    )
    book.add_item(css)

    spine_items = []
    all_items = main_chapters + extras

    for idx, (name, body) in enumerate(all_items):
        body_clean = body.replace("\r\n", "\n").replace("\r", "\n")
        paras = []
        for line in body_clean.split("\n"):
            line = line.strip()
            if line:
                paras.append(html.escape(line))

        content = f"<h1>{html.escape(name)}</h1>\n"
        for p in paras:
            content += f"<p>{p}</p>\n"

        ep_ch = epub.EpubHtml(
            title=name,
            file_name=f"chapter_{idx + 1:04d}.xhtml",
            lang="zh-CN",
        )
        ep_ch.content = (
            '<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="zh-CN">\n'
            f"<head><title>{html.escape(name)}</title>\n"
            '<link rel="stylesheet" type="text/css" href="style/default.css"/></head>\n'
            f"<body>{content}</body></html>"
        )
        book.add_item(ep_ch)
        spine_items.append(ep_ch)

    book.toc = spine_items
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())
    book.spine = ["nav"] + spine_items

    epub.write_epub(str(OUTPUT), book)
    print(f"\nEPUB written: {OUTPUT} ({OUTPUT.stat().st_size / 1024 / 1024:.1f} MB)")


if __name__ == "__main__":
    build_epub()
