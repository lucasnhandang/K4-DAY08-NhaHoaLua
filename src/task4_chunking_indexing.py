"""
Task 4 — Chunking & Indexing vào Vector Store.

Hướng dẫn:
    1. Đọc toàn bộ markdown files từ data/standardized/
    2. Chọn 1 chunking strategy (giải thích lý do)
    3. Chọn 1 embedding model (giải thích lý do)
    4. Index vào vector store (ChromaDB khuyến cáo — đơn giản, local, không cần Docker)

Chunking options (langchain-text-splitters):
    - RecursiveCharacterTextSplitter: an toàn, phổ biến
    - MarkdownHeaderTextSplitter: tốt cho file có heading
    - SemanticChunker: dùng embedding để tách (nâng cao)

Embedding model options:
    - sentence-transformers/all-MiniLM-L6-v2 (384 dim, nhẹ)
    - BAAI/bge-m3 (1024 dim, multilingual, tốt cho cả tiếng Việt lẫn tiếng Anh)
    - OpenAI text-embedding-3-small (1536 dim, API)

Vector store options:
    - ChromaDB (khuyến cáo: đơn giản, local persistent, không cần Docker)
    - Weaviate (hỗ trợ hybrid search built-in, cần Docker/Cloud)
    - FAISS (chỉ dense search)

Cài đặt:
    pip install langchain-text-splitters sentence-transformers chromadb

Lưu ý quan trọng: nếu sau này đổi corpus (đổi chủ đề, thêm/bớt tài liệu), phải XÓA
chroma_db/ cũ trước khi reindex — nếu không, chunk cũ và mới sẽ tồn tại lẫn lộn
trong cùng collection, retrieval sẽ trả về kết quả rác từ dữ liệu cũ.
"""

import re
from pathlib import Path

STANDARDIZED_DIR = Path(__file__).parent.parent / "data" / "standardized"
CHROMA_DIR = Path(__file__).parent.parent / "chroma_db"


# =============================================================================
# CONFIGURATION — Giải thích lựa chọn của bạn trong comment
# =============================================================================

# Chunking strategy: RecursiveCharacterTextSplitter
#   - An toàn, phổ biến nhất, hoạt động tốt với mọi loại document
#   - Thử tách theo paragraph → heading → câu → từ (từ rộng đến hẹp)
#   - Phù hợp vì corpus có cả legal (đoạn dài, formal) lẫn news (đoạn ngắn, tự nhiên)
CHUNK_SIZE = 800        # ~800 chars: đủ ngữ cảnh cho một ý/điều khoản hoàn chỉnh
CHUNK_OVERLAP = 100     # Giữ ngữ cảnh khi câu/điều khoản nằm sát ranh giới chunk
CHUNKING_METHOD = "recursive"  # "recursive" | "markdown_header" | "semantic"

# Embedding model: BAAI/bge-m3
#   - Multilingual: hỗ trợ tốt tiếng Việt lẫn tiếng Anh (corpus có cả 2)
#   - 1024 dim: đủ lớn để biểu diễn ngữ nghĩa phong phú, không quá nặng
#   - Local model (không cần API key), chạy offline được
EMBEDDING_MODEL = "BAAI/bge-m3"
EMBEDDING_DIM = 1024

# TODO: Chọn vector store
VECTOR_STORE = "chromadb"  # "chromadb" | "weaviate" | "faiss"
COLLECTION_NAME = "ecommerce_support_docs"


# =============================================================================
# IMPLEMENTATION
# =============================================================================

VALID_CUSTOMER_ROLES = {"buyer", "seller", "both"}

# Hai nguồn dữ liệu hiện dùng hai kiểu metadata:
#   **customer_role:** buyer   (news)
#   Customer role: seller     (legal)
METADATA_KEY_MAP = {
    "doc id": "doc_id",
    "customer role": "customer_role",
    "category": "category",
    "platform": "platform",
    "source": "source_url",
    "source url": "source_url",
    "crawled": "crawled_at",
    "retrieved at": "retrieved_at",
    "document version": "document_version",
}


def _parse_metadata(content: str) -> dict[str, str]:
    """Đọc metadata ở phần đầu Markdown và chuẩn hóa tên trường."""
    metadata = {}
    # Metadata của corpus đều nằm trước heading nội dung thứ hai / 30 dòng đầu.
    for raw_line in content.splitlines()[:30]:
        line = raw_line.strip()
        match = re.match(r"^(?:\*\*)?([^:*]+?)(?:\*\*)?\s*:\s*(.*)$", line)
        if not match:
            continue

        raw_key = match.group(1).strip().lower().replace("_", " ")
        key = METADATA_KEY_MAP.get(raw_key)
        if not key:
            continue

        value = match.group(2).strip().strip("*").strip()
        if value:
            metadata[key] = value
    return metadata


def load_documents() -> list[dict]:
    """
    Đọc toàn bộ markdown files từ data/standardized/.

    Returns:
        List of {'content': str, 'metadata': dict}. Metadata gồm tối thiểu:
        source, type, doc_id, customer_role, category, platform.
    """
    documents = []
    for md_file in sorted(STANDARDIZED_DIR.rglob("*.md")):
        content = md_file.read_text(encoding="utf-8")
        # Xác định loại document dựa trên cấu trúc thư mục
        doc_type = "legal" if md_file.parent.name == "legal" else "news"
        parsed = _parse_metadata(content)
        customer_role = parsed.get("customer_role", "").lower()
        if customer_role not in VALID_CUSTOMER_ROLES:
            raise ValueError(
                f"{md_file}: customer_role phải là buyer/seller/both, "
                f"nhận được {customer_role!r}"
            )

        metadata = {
            "source": md_file.name,
            "type": doc_type,
            "doc_id": parsed.get("doc_id", md_file.stem),
            "customer_role": customer_role,
            "category": parsed.get("category", "uncategorized"),
            "platform": parsed.get("platform", "unknown"),
        }
        # Chroma chỉ nhận metadata scalar; các giá trị parse ở đây đều là string.
        metadata.update({k: v for k, v in parsed.items() if k not in metadata})
        documents.append({
            "content": content,
            "metadata": metadata,
        })
    return documents


def chunk_documents(documents: list[dict]) -> list[dict]:
    """
    Chunk documents theo strategy đã chọn.

    Returns:
        List of {'content': str, 'metadata': dict} — mỗi item là 1 chunk
    """
    from langchain_text_splitters import RecursiveCharacterTextSplitter

    # RecursiveCharacterTextSplitter: an toàn, phổ biến nhất.
    # Thử tách theo "\n\n" trước (paragraph), rồi "\n" (heading), ". " (câu), " " (từ).
    # chunk_size=800: vừa đủ cho 1 chunk chứa ngữ cảnh liên quan,
    #   không quá ngắn (mất context) cũng không quá dài (phá cấu trúc embedding).
    # chunk_overlap=100: giữ liên tục ngữ cảnh ở ranh giới chunk.
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", ". ", " ", ""]
    )

    chunks = []
    for doc in documents:
        splits = splitter.split_text(doc["content"])
        for i, chunk_text in enumerate(splits):
            # Bỏ qua chunk quá ngắn (dưới 20 ký tự) — thường là fragment rác
            if len(chunk_text.strip()) < 20:
                continue
            chunks.append({
                "content": chunk_text,
                "metadata": {**doc["metadata"], "chunk_index": i}
            })
    return chunks


def embed_chunks(chunks: list[dict]) -> list[dict]:
    """
    Embed toàn bộ chunks bằng model đã chọn.

    Returns:
        Mỗi chunk dict được thêm key 'embedding': list[float]
    """
    from sentence_transformers import SentenceTransformer

    # BAAI/bge-m3: model multilingual, hỗ trợ tốt cả tiếng Việt lẫn tiếng Anh.
    # Dimension 1024 — đủ lớn để biểu diễn ngữ nghĩa phong phú,
    #   nhưng không quá lớn gây lãng phí bộ nhớ/search time.
    model = SentenceTransformer(EMBEDDING_MODEL)
    texts = [c["content"] for c in chunks]
    embeddings = model.encode(texts, show_progress_bar=True, batch_size=32)
    for chunk, emb in zip(chunks, embeddings):
        chunk["embedding"] = emb.tolist()
    return chunks


def index_to_vectorstore(chunks: list[dict]):
    """
    Lưu chunks vào vector store đã chọn.
    """
    import chromadb

    # ChromaDB: vector store local, đơn giản, không cần Docker/server.
    # PersistentClient lưu xuống disk tại CHROMA_DIR, giữ data giữa các lần chạy.
    # Hnsw space "cosine": phù hợp cho embeddings đã normalize (từ bge-m3).
    CHROMA_DIR.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    collection = client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )

    # Tạo ID ổn định cho mỗi chunk từ doc_id đã chuẩn hóa.
    ids = [
        f"{c['metadata']['doc_id']}_chunk_{c['metadata']['chunk_index']}"
        for c in chunks
    ]
    collection.upsert(
        ids=ids,
        documents=[c["content"] for c in chunks],
        embeddings=[c["embedding"] for c in chunks],
        metadatas=[c["metadata"] for c in chunks],
    )
    print(f"  → Upserted {len(ids)} chunks into '{COLLECTION_NAME}' collection")


def run_pipeline():
    """Chạy toàn bộ pipeline: load → chunk → embed → index."""
    print("=" * 50)
    print("Task 4: Chunking & Indexing")
    print(f"  Chunking: {CHUNKING_METHOD} (size={CHUNK_SIZE}, overlap={CHUNK_OVERLAP})")
    print(f"  Embedding: {EMBEDDING_MODEL} (dim={EMBEDDING_DIM})")
    print(f"  Vector Store: {VECTOR_STORE}")
    print("=" * 50)

    docs = load_documents()
    print(f"\n✓ Loaded {len(docs)} documents")

    chunks = chunk_documents(docs)
    print(f"✓ Created {len(chunks)} chunks")

    chunks = embed_chunks(chunks)
    print(f"✓ Embedded {len(chunks)} chunks")

    index_to_vectorstore(chunks)
    print("✓ Indexed to vector store")


if __name__ == "__main__":
    run_pipeline()
