"""
Task 1 — Thu thập văn bản chính sách thương mại điện tử / hỗ trợ khách hàng.

Hướng dẫn:
    1. Tìm tối thiểu 3 văn bản chính sách (PDF/DOCX) từ trang chính thức của một sàn TMĐT.
    2. Tải về và lưu vào data/landing/legal/
    3. Đặt tên file rõ ràng, không dấu, mô tả đúng nội dung.

Gợi ý nguồn (ví dụ trang công khai Shopee Vietnam — help.shopee.vn):
    - https://help.shopee.vn/portal/4/article/77251 (Chính sách trả hàng và hoàn tiền)
    - https://help.shopee.vn/portal/4/article/79198 (Phương thức thanh toán)
    - https://help.shopee.vn/portal/4/article/77244 (Chính sách bảo mật)

Gợi ý văn bản (chủ đề chính sách thương mại điện tử):
    - Chính sách đổi trả/hoàn tiền (Returns/Refund Policy)
    - Phương thức thanh toán (Payment Methods)
    - Chính sách bảo mật (Privacy Policy)
    - Quy định đăng bán sản phẩm cho người bán (Seller Listing Regulations)

Nhớ gắn metadata `customer_role` (`buyer`/`seller`/`both`) cho từng tài liệu — yêu cầu riêng
của K4 Variant (kế thừa từ Lab 07), cần thiết để viết benchmark query dùng metadata_filter.

Lưu ý: một số trang help center dùng JavaScript render nội dung (SPA) — crawl về chỉ thấy
tiêu đề mà không có nội dung thật. Đổi sang bài viết khác cùng domain thay vì cố xử lý,
và chỉ dùng nguồn công khai/được phép chia sẻ.
"""

import json
import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data" / "landing" / "legal"
DAY7_CORPUS_DIR = Path(
    os.getenv(
        "DAY7_CORPUS_DIR",
        PROJECT_ROOT.parent
        / "DAY07-2A202601050-DangVanNhan"
        / "data"
        / "k4_ecommerce",
    )
)

LEGAL_DOCUMENTS = [
    {
        "doc_id": "shopee-seller-listing-rules",
        "title": "Quy định đăng bán sản phẩm",
        "source_url": "https://help.shopee.vn/portal/4/article/77246",
        "customer_role": "seller",
        "category": "listing-policy",
        "source_file": "shopee-seller-listing-rules.md",
        "output_file": "seller-listing-rules-shopee.pdf",
    },
    {
        "doc_id": "shopee-seller-prohibited-products",
        "title": "Chính sách cấm/hạn chế sản phẩm",
        "source_url": "https://help.shopee.vn/portal/4/article/77247",
        "customer_role": "seller",
        "category": "prohibited-products",
        "source_file": "shopee-seller-prohibited-products.md",
        "output_file": "prohibited-products-policy-shopee.pdf",
    },
    {
        "doc_id": "shopee-seller-antifraud",
        "title": "Chính sách chống hành vi gian lận",
        "source_url": "https://help.shopee.vn/portal/4/article/140097",
        "customer_role": "seller",
        "category": "seller-compliance",
        "source_file": "shopee-seller-antifraud.md",
        "output_file": "seller-antifraud-policy-shopee.pdf",
    },
    {
        "doc_id": "shopee-seller-responsibilities-fees",
        "title": "Trách nhiệm và phí của người bán",
        "source_url": "https://help.shopee.vn/portal/4/article/77243",
        "customer_role": "seller",
        "category": "seller-responsibilities-fees",
        "source_file": "shopee-seller-responsibilities-fees.md",
        "output_file": "seller-responsibilities-fees-shopee.pdf",
    },
]

FONT_CANDIDATES = [
    Path("/System/Library/Fonts/Supplemental/Arial Unicode.ttf"),
    Path("/System/Library/Fonts/Supplemental/Arial.ttf"),
    Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
]


def setup_directory():
    """Tạo thư mục data/landing/legal/ nếu chưa có."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    print(f"✓ Thư mục đã sẵn sàng: {DATA_DIR}")


def find_unicode_font() -> Path:
    """Tìm font hỗ trợ tiếng Việt để fpdf2 có thể tạo PDF Unicode."""
    for font_path in FONT_CANDIDATES:
        if font_path.is_file():
            return font_path
    raise FileNotFoundError(
        "Không tìm thấy font Unicode. Hãy cài Arial, Noto Sans hoặc DejaVu Sans "
        "và thêm đường dẫn font vào FONT_CANDIDATES."
    )


def split_front_matter(markdown: str) -> tuple[dict[str, str], str]:
    """Tách YAML front matter đơn giản từ corpus Markdown của Day 7."""
    lines = markdown.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}, markdown

    try:
        end = next(i for i, line in enumerate(lines[1:], 1) if line.strip() == "---")
    except StopIteration:
        return {}, markdown

    metadata = {}
    for line in lines[1:end]:
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        metadata[key.strip()] = value.strip().strip('"').strip("'")
    return metadata, "\n".join(lines[end + 1 :]).strip()


def markdown_to_pdf(source_path: Path, output_path: Path, document: dict) -> dict:
    """Chuyển một bản Markdown đã làm sạch thành PDF có metadata nguồn."""
    from fpdf import FPDF

    source_metadata, body = split_front_matter(
        source_path.read_text(encoding="utf-8")
    )
    metadata = {
        **source_metadata,
        "doc_id": document["doc_id"],
        "title": document["title"],
        "source_url": document["source_url"],
        "customer_role": document["customer_role"],
        "category": document["category"],
        "platform": source_metadata.get("platform", "shopee-vn"),
    }

    pdf = FPDF(format="A4")
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.set_title(metadata["title"])
    pdf.set_subject(
        f"Source: {metadata['source_url']} | customer_role: {metadata['customer_role']}"
    )
    pdf.set_creator("K4 Day 8 RAG Lab - derived from public Shopee page")
    pdf.add_page()
    pdf.add_font("Unicode", fname=str(find_unicode_font()))
    pdf.set_font("Unicode", size=11)

    header_lines = [
        metadata["title"],
        "",
        f"Source URL: {metadata['source_url']}",
        f"Retrieved at: {metadata.get('retrieved_at', 'not-stated')}",
        f"Document version: {metadata.get('document_version', 'not-stated')}",
        f"Customer role: {metadata['customer_role']}",
        f"Category: {metadata['category']}",
        f"Platform: {metadata['platform']}",
        "",
    ]

    for line in [*header_lines, *body.splitlines()]:
        pdf.multi_cell(0, 5.5, text=line or " ", new_x="LMARGIN", new_y="NEXT")

    pdf.output(str(output_path))
    return {
        key: metadata.get(key, "")
        for key in (
            "doc_id",
            "title",
            "source_url",
            "retrieved_at",
            "document_version",
            "customer_role",
            "category",
            "platform",
        )
    } | {"file_path": str(output_path.relative_to(PROJECT_ROOT))}


def collect_legal_documents() -> list[dict]:
    """Tạo bốn PDF chính sách người bán từ corpus Day 7 đã làm sạch."""
    setup_directory()
    if not DAY7_CORPUS_DIR.is_dir():
        raise FileNotFoundError(
            f"Không tìm thấy corpus Day 7 tại {DAY7_CORPUS_DIR}. "
            "Có thể đặt biến DAY7_CORPUS_DIR trỏ tới data/k4_ecommerce."
        )

    manifest = []
    for document in LEGAL_DOCUMENTS:
        source_path = DAY7_CORPUS_DIR / document["source_file"]
        if not source_path.is_file():
            raise FileNotFoundError(f"Thiếu tài liệu nguồn: {source_path}")

        output_path = DATA_DIR / document["output_file"]
        record = markdown_to_pdf(source_path, output_path, document)
        manifest.append(record)
        print(f"✓ Đã tạo: {output_path}")

    manifest_path = DATA_DIR / "sources.json"
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"✓ Manifest: {manifest_path}")
    return manifest


if __name__ == "__main__":
    collect_legal_documents()
