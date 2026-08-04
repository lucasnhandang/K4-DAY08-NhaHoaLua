"""
Task 5 — Semantic Search Module.

Tìm kiếm ngữ nghĩa (dense retrieval) trên vector store sử dụng ChromaDB
và embedding model BAAI/bge-m3 (tương thích với Task 4).

Yêu cầu:
    - Input: query string + top_k
    - Output: danh sách chunks có score, sorted descending
    - Phải tương thích với embedding model và vector store ở Task 4
"""

from pathlib import Path

CHROMA_DIR = Path(__file__).parent.parent / "chroma_db"
EMBEDDING_MODEL = "BAAI/bge-m3"
COLLECTION_NAME = "ecommerce_support_docs"


def _get_collection():
    """Lấy ChromaDB collection đã index ở Task 4."""
    import chromadb

    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    return client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )


def _get_embedding_model():
    """Load embedding model BAAI/bge-m3 (tương tự Task 4)."""
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(EMBEDDING_MODEL)


def semantic_search(query: str, top_k: int = 10) -> list[dict]:
    """
    Tìm kiếm ngữ nghĩa sử dụng vector similarity.

    Args:
        query: Câu truy vấn
        top_k: Số lượng kết quả tối đa

    Returns:
        List of {
            'content': str,      # Nội dung chunk
            'score': float,      # Cosine similarity score
            'metadata': dict     # source, doc_type, chunk_index
        }
        Sorted by score descending.
    """
    model = _get_embedding_model()
    collection = _get_collection()

    # Bước 1: Embed query bằng cùng model ở Task 4
    query_vector = model.encode(query).tolist()

    # Bước 2: Query vector store (cosine similarity)
    # ChromaDB trả về cosine distance; chuyển sang similarity: score = 1 - distance
    results = collection.query(
        query_embeddings=[query_vector],
        n_results=top_k,
        include=["documents", "metadatas", "distances"],
    )

    # Bước 3: Map kết quả thành list dicts
    output = []
    if results["documents"] and results["documents"][0]:
        for doc, meta, dist in zip(
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0],
        ):
            # cosine distance → similarity: score = 1 - distance
            score = max(0.0, 1.0 - dist)
            output.append({
                "content": doc,
                "score": round(score, 4),
                "metadata": meta,
            })

    # Sort theo score giảm dần
    output.sort(key=lambda x: x["score"], reverse=True)
    return output[:top_k]


if __name__ == "__main__":
    # Test
    results = semantic_search("quy định trả hàng hoàn tiền shopee", top_k=5)
    for r in results:
        print(f"[{r['score']:.3f}] {r['content'][:100]}...")
