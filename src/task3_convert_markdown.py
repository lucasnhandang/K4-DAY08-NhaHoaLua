"""
Task 3 — Convert toàn bộ file trong data/landing/ thành Markdown.

Sử dụng MarkItDown của Microsoft:
    https://github.com/microsoft/markitdown

Cài đặt:
    pip install "markitdown[pdf]"
    # Lưu ý: cần extra [pdf] để convert được file PDF. Chỉ "pip install markitdown"
    # (không có extra) sẽ báo MissingDependencyException khi convert PDF, dù JSON/DOCX
    # vẫn convert bình thường.

Hướng dẫn:
    1. Scan toàn bộ file trong data/landing/ (PDF, DOCX, JSON)
    2. Convert sang Markdown
    3. Lưu vào data/standardized/ giữ nguyên cấu trúc thư mục
"""

import json
from pathlib import Path

from markitdown import MarkItDown

LANDING_DIR = Path(__file__).parent.parent / "data" / "landing"
OUTPUT_DIR = Path(__file__).parent.parent / "data" / "standardized"


def convert_legal_docs():
    """Convert PDF/DOCX files trong data/landing/legal/ sang markdown."""
    legal_dir = LANDING_DIR / "legal"
    output_dir = OUTPUT_DIR / "legal"
    output_dir.mkdir(parents=True, exist_ok=True)

    md = MarkItDown()
    count = 0

    for filepath in legal_dir.iterdir():
        if filepath.suffix.lower() in (".pdf", ".docx", ".doc"):
            print(f"Converting: {filepath.name}")
            try:
                result = md.convert(str(filepath))
                output_path = output_dir / f"{filepath.stem}.md"
                output_path.write_text(result.text_content, encoding="utf-8")
                print(f"  [OK] Saved: {output_path} ({len(result.text_content)} chars)")
                count += 1
            except Exception as e:
                print(f"  [ERROR] {e}")

    return count


def convert_news_articles():
    """Convert JSON crawled articles trong data/landing/news/ sang markdown."""
    news_dir = LANDING_DIR / "news"
    output_dir = OUTPUT_DIR / "news"
    output_dir.mkdir(parents=True, exist_ok=True)
    count = 0

    for filepath in news_dir.iterdir():
        if filepath.suffix.lower() == ".json" and filepath.name != "sources.json":
            print(f"Converting: {filepath.name}")
            try:
                data = json.loads(filepath.read_text(encoding="utf-8"))
                output_path = output_dir / f"{filepath.stem}.md"

                # Thêm metadata header
                header = f"# {data.get('title', 'Unknown')}\n\n"
                header += f"**doc_id:** {data.get('doc_id', 'N/A')}\n"
                header += f"**customer_role:** {data.get('customer_role', 'N/A')}\n"
                header += f"**category:** {data.get('category', 'N/A')}\n"
                header += f"**platform:** {data.get('platform', 'N/A')}\n"
                header += f"**Source:** {data.get('url', 'N/A')}\n"
                header += f"**Crawled:** {data.get('date_crawled', 'N/A')}\n\n---\n\n"

                content = header + data.get("content_markdown", "")
                output_path.write_text(content, encoding="utf-8")
                print(f"  [OK] Saved: {output_path} ({len(content)} chars)")
                count += 1
            except Exception as e:
                print(f"  [ERROR] {e}")

    return count


def convert_all():
    """Convert toàn bộ files."""
    print("=" * 50)
    print("Task 3: Convert to Markdown (MarkItDown)")
    print("=" * 50)

    total = 0

    try:
        print("\n--- Legal Documents ---")
        total += convert_legal_docs()
    except Exception as e:
        print(f"  [ERROR] Legal docs: {e}")

    try:
        print("\n--- News Articles ---")
        total += convert_news_articles()
    except Exception as e:
        print(f"  [ERROR] News articles: {e}")

    # Tong ket
    print("\n" + "=" * 50)
    print(f"[DONE] Converted {total} files")
    print(f"Output: {OUTPUT_DIR}")


if __name__ == "__main__":
    convert_all()
