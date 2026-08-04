"""
Task 5 — Semantic Search Module.

Tìm kiếm ngữ nghĩa (dense retrieval) trên vector store sử dụng ChromaDB
và embedding model BAAI/bge-m3 (tương thích với Task 4).

Hỗ trợ 2 phương pháp:
    1. Basic Semantic Search: Embed query → vector search
    2. HyDE (Hypothetical Document Embeddings): LLM sinh câu trả lời giả định → embed → search
"""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

CHROMA_DIR = Path(__file__).parent.parent / "chroma_db"
EMBEDDING_MODEL = "BAAI/bge-m3"
COLLECTION_NAME = "ecommerce_support_docs"

# HyDE config: LLM để sinh hypothetical document
HYDE_LLM_MODEL = "openai/gpt-4o-mini"


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


def _generate_hypothetical_document(query: str) -> str:
    """
    Dùng LLM sinh một đoạn văn trả lời giả định cho query.
    Đây là bước cốt lõi của HyDE — tạo 'hypothetical document'
    để embed thay vì embed query gốc.
    """
    from openai import OpenAI

    api_key = os.getenv("OPENROUTER_API_KEY") or os.getenv("OPENAI_API_KEY")
    client = OpenAI(api_key=api_key, base_url="https://openrouter.ai/api/v1")

    prompt = (
        f"Hãy viết một đoạn ngắn (100-200 từ) trả lời cho câu hỏi sau. "
        f"Đoạn văn phải giống như trích từ tài liệu chính sách thương mại điện tử.\n\n"
        f"Câu hỏi: {query}"
    )

    response = client.chat.completions.create(
        model=HYDE_LLM_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
        max_tokens=300,
    )
    return response.choices[0].message.content


def semantic_search(query: str, top_k: int = 10, use_hyde: bool = False) -> list[dict]:
    """
    Tìm kiếm ngữ nghĩa sử dụng vector similarity.

    Args:
        query: Câu truy vấn
        top_k: Số lượng kết quả tối đa
        use_hyde: Nếu True, dùng HyDE (LLM sinh hypothetical doc trước khi search)

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

    # Bước 1: Embed — nếu HyDE thì embed hypothetical doc, nếu không thì embed query
    if use_hyde:
        hypothetical_doc = _generate_hypothetical_document(query)
        search_text = hypothetical_doc
    else:
        search_text = query

    query_vector = model.encode(search_text).tolist()

    # Bước 2: Query vector store (cosine similarity)
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
            score = max(0.0, 1.0 - dist)
            output.append({
                "content": doc,
                "score": round(score, 4),
                "metadata": meta,
            })

    output.sort(key=lambda x: x["score"], reverse=True)
    return output[:top_k]


if __name__ == "__main__":
    import sys

    query = "quy định trả hàng hoàn tiền shopee"
    if len(sys.argv) > 1:
        query = sys.argv[1]

    print("=" * 60)
    print("BASIC SEMANTIC SEARCH")
    print("=" * 60)
    results = semantic_search(query, top_k=5, use_hyde=False)
    for r in results:
        print(f"[{r['score']:.3f}] {r['content'][:100]}...")

    print("\n" + "=" * 60)
    print("HyDE SEARCH (Hypothetical Document Embeddings)")
    print("=" * 60)
    results = semantic_search(query, top_k=5, use_hyde=True)
    for r in results:
        print(f"[{r['score']:.3f}] {r['content'][:100]}...")
