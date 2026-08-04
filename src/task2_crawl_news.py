"""
Task 2 — Crawl bài viết/hướng dẫn hỗ trợ khách hàng về thương mại điện tử.

Hướng dẫn:
    1. Crawl tối thiểu 5 bài viết từ trung tâm trợ giúp công khai của một sàn TMĐT.
    2. Sử dụng Crawl4AI hoặc thư viện crawling tương tự.
    3. Lưu output vào data/landing/news/
    4. Mỗi bài lưu 1 file JSON với metadata (url, title, date_crawled, content).

Cài đặt:
    pip install crawl4ai
    playwright install chromium   # bắt buộc — pip install crawl4ai KHÔNG tự tải browser binary,
                                   # thiếu bước này sẽ báo lỗi
                                   # "BrowserType.launch: Executable doesn't exist"

Gợi ý chủ đề: theo dõi đơn hàng, đổi phương thức thanh toán, bằng chứng hoàn tiền,
mua hàng xuyên biên giới.

Lưu ý: một số trang help center dùng JavaScript render (SPA) — nếu crawl về chỉ thấy
tiêu đề mà không có nội dung, đổi sang bài viết khác cùng domain thay vì cố xử lý.
"""

import asyncio
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data" / "landing" / "news"

# Múi giờ Việt Nam (UTC+7)
VN_TZ = timezone(timedelta(hours=7))


def setup_directory():
    """Tạo thư mục data/landing/news/ nếu chưa có."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)


# Danh sách URL bài viết từ Shopee Vietnam Help Center
ARTICLE_URLS = [
    # Buyer support articles
    "https://help.shopee.vn/portal/4/article/79198",   # Phương thức thanh toán
    "https://help.shopee.vn/portal/4/article/79182",   # Hủy đơn hàng
    "https://help.shopee.vn/portal/4/article/79233",   # Gửi yêu cầu trả hàng/hoàn tiền
    "https://help.shopee.vn/portal/4/article/189473",  # Thời gian nhận tiền hoàn

    # Supporting policy articles
    "https://help.shopee.vn/portal/4/article/77250",   # Chính sách vận chuyển
    "https://help.shopee.vn/portal/4/article/77251",   # Chính sách trả hàng/hoàn tiền
]


async def crawl_article(url: str) -> dict:
    """
    Crawl một bài viết và trả về dict chứa metadata + content.

    Returns:
        {
            "url": str,
            "title": str,
            "date_crawled": str (ISO format),
            "content_markdown": str
        }
    """
    from crawl4ai import AsyncWebCrawler

    async with AsyncWebCrawler() as crawler:
        result = await crawler.arun(url=url)

    if not getattr(result, "success", True):
        error = getattr(result, "error_message", "Unknown crawl error")
        raise RuntimeError(f"Không thể crawl {url}: {error}")

    # Crawl4AI bản cũ trả markdown là str; bản mới trả
    # MarkdownGenerationResult chứa raw_markdown/fit_markdown.
    markdown_result = getattr(result, "markdown", "")
    if isinstance(markdown_result, str):
        content_markdown = markdown_result
    elif isinstance(markdown_result, dict):
        content_markdown = (
            markdown_result.get("raw_markdown")
            or markdown_result.get("fit_markdown")
            or ""
        )
    else:
        content_markdown = (
            getattr(markdown_result, "raw_markdown", None)
            or getattr(markdown_result, "fit_markdown", None)
            or str(markdown_result or "")
        )

    content_markdown = content_markdown.strip()
    if not content_markdown:
        raise RuntimeError(f"Crawl thành công nhưng không lấy được nội dung từ {url}")

    metadata = getattr(result, "metadata", None) or {}
    title = metadata.get("title") or metadata.get("og:title") or "Unknown"

    return {
        "url": url,
        "title": title,
        "date_crawled": datetime.now(VN_TZ).isoformat(),
        "content_markdown": content_markdown,
    }


async def crawl_all():
    """Crawl toàn bộ bài viết trong ARTICLE_URLS."""
    setup_directory()

    print(f"Bắt đầu crawl {len(ARTICLE_URLS)} bài viết từ Shopee Help Center...")
    print("-" * 60)

    success_count = 0
    fail_count = 0

    for i, url in enumerate(ARTICLE_URLS, 1):
        print(f"\n[{i}/{len(ARTICLE_URLS)}] Crawling: {url}")
        try:
            article = await crawl_article(url)

            # Kiểm tra có nội dung không (tránh SPA render rỗng)
            if not article["content_markdown"] or len(article["content_markdown"].strip()) < 50:
                print(f"  ⚠ Cảnh báo: Nội dung quá ngắn, có thể trang dùng JS render")
                print(f"    Title: {article['title']}")

            # Lưu file JSON
            filename = f"article_{i:02d}.json"
            filepath = DATA_DIR / filename
            filepath.write_text(
                json.dumps(article, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            print(f"  ✓ Saved: {filepath}")
            print(f"    Title: {article['title']}")
            print(f"    Content length: {len(article['content_markdown'])} chars")
            success_count += 1

        except Exception as e:
            print(f"  ✗ Lỗi: {e}")
            fail_count += 1

    # Tổng kết
    print("\n" + "=" * 60)
    print(f"Hoàn thành! Thành công: {success_count}, Thất bại: {fail_count}")
    print(f"Thư mục output: {DATA_DIR}")


if __name__ == "__main__":
    if not ARTICLE_URLS:
        print("⚠ Hãy điền ARTICLE_URLS trước khi chạy!")
        print("Gợi ý: tìm trang hướng dẫn/hỗ trợ khách hàng trên help center của sàn TMĐT")
    else:
        asyncio.run(crawl_all())
