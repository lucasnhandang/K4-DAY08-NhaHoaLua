"""
Task 7 — Reranking Module.

Chọn 1 trong các phương pháp:
    - Cross-encoder reranker: Jina Reranker v2 (multilingual) — cần JINA_API_KEY
    - MMR (Maximal Marginal Relevance): tự implement
    - RRF (Reciprocal Rank Fusion): tự implement — khuyến nghị vì không cần API key

Nếu dùng MMR hoặc RRF, đảm bảo hiểu và giải thích được cơ chế.

Lưu ý quan trọng về RRF (sẽ dùng lại ở Task 9): điểm RRF fused CHỈ phụ thuộc thứ hạng,
không phải độ tương đồng thật. Top-1 sau khi fuse luôn xấp xỉ 1/(k+1) ≈ 0.0164 (k=60),
bất kể nội dung đó có thật sự liên quan đến câu hỏi hay không. Đừng dùng điểm RRF để
quyết định fallback ở Task 9 — xem ghi chú ở đó.
"""

import os
import unicodedata
from typing import Hashable

from dotenv import load_dotenv

load_dotenv()


def _normalize_vietnamese(text: str) -> str:
    """
    Bỏ dấu tiếng Việt để Jina model xử lý tốt hơn.

    Jina Reranker v2 xử lý kém text có dấu tiếng Việt.
    Bỏ dấu giúp model tập trung vào semantic thay vì diacritics.
    """
    # decompose -> remove combining marks -> recompose
    nfkd = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in nfkd if unicodedata.category(ch) != "Mn")


def rerank_cross_encoder(
    query: str, candidates: list[dict], top_k: int = 5
) -> list[dict]:
    """
    Rerank candidates sử dụng cross-encoder model.

    Strategy:
        - Nếu có JINA_API_KEY → dùng Jina Reranker v2 API (nhanh, chính xác)
        - Nếu không có → fallback về RRF (không cần API key)

    Args:
        query: Câu truy vấn
        candidates: List of {'content': str, 'score': float, 'metadata': dict}
        top_k: Số lượng kết quả sau rerank

    Returns:
        List of top_k candidates, re-scored và sorted by rerank_score descending.
    """
    jina_api_key = os.getenv("JINA_API_KEY")

    if jina_api_key:
        return _rerank_jina_api(query, candidates, top_k, jina_api_key)
    else:
        print("  ℹ No JINA_API_KEY found — falling back to RRF reranking")
        return rerank_rrf([candidates], top_k=top_k)


def _rerank_jina_api(
    query: str, candidates: list[dict], top_k: int, api_key: str
) -> list[dict]:
    """
    Jina Reranker v2 API — cross-encoder multilingual.

    API docs: https://jina.ai/reranker
    Model: jina-reranker-v2-base-multilingual (hỗ trợ 100+ ngôn ngữ)

    Returns:
        List of top_k candidates với relevance_score từ Jina.
        Nếu API fail (402 insufficient balance, 429 rate limit, etc.) → fallback RRF.
    """
    import requests

    try:
        # Jina model xử lý kém Vietnamese có dấu → normalize trước khi gửi
        normalized_query = _normalize_vietnamese(query)
        normalized_docs = [_normalize_vietnamese(c["content"]) for c in candidates]

        response = requests.post(
            "https://api.jina.ai/v1/rerank",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": "jina-reranker-v2-base-multilingual",
                "query": normalized_query,
                "documents": normalized_docs,
                "top_n": top_k,
            },
            timeout=30,
        )
        response.raise_for_status()

        data = response.json()
        reranked = data.get("results", [])

        return [
            {
                **candidates[r["index"]],
                "rerank_score": r["relevance_score"],
                "score": r["relevance_score"],  # Override original score
            }
            for r in reranked
        ]

    except requests.exceptions.HTTPError as e:
        # 402 (insufficient balance), 429 (rate limit), 401 (invalid key)
        print(f"  ⚠ Jina API error: {e} — falling back to RRF")
        return rerank_rrf([candidates], top_k=top_k)
    except requests.exceptions.RequestException as e:
        # Network error, timeout, etc.
        print(f"  ⚠ Jina API unreachable: {e} — falling back to RRF")
        return rerank_rrf([candidates], top_k=top_k)


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    """Tính cosine similarity giữa hai vectors."""
    dot_product = sum(x * y for x, y in zip(a, b))
    norm_a = sum(x * x for x in a) ** 0.5
    norm_b = sum(x * x for x in b) ** 0.5
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot_product / (norm_a * norm_b)


def rerank_mmr(
    query_embedding: list[float],
    candidates: list[dict],
    top_k: int = 5,
    lambda_param: float = 0.7,
) -> list[dict]:
    """
    Maximal Marginal Relevance — chọn candidates vừa relevant vừa diverse.

    MMR = λ * sim(query, doc) - (1-λ) * max(sim(doc, selected_docs))

    Args:
        query_embedding: Vector embedding của query
        candidates: List of {'content': str, 'score': float, 'embedding': list, 'metadata': dict}
        top_k: Số lượng kết quả
        lambda_param: Trade-off giữa relevance (1.0) và diversity (0.0)

    Returns:
        List of top_k candidates selected by MMR.
    """
    if top_k <= 0 or not candidates:
        return []

    selected = []
    remaining = list(range(len(candidates)))

    for _ in range(min(top_k, len(candidates))):
        best_idx = None
        best_score = float("-inf")

        for idx in remaining:
            # Relevance to query
            relevance = _cosine_similarity(query_embedding, candidates[idx]["embedding"])

            # Max similarity to already selected
            max_sim_to_selected = 0.0
            for sel_idx in selected:
                sim = _cosine_similarity(
                    candidates[idx]["embedding"], candidates[sel_idx]["embedding"]
                )
                max_sim_to_selected = max(max_sim_to_selected, sim)

            # MMR score
            mmr_score = lambda_param * relevance - (1 - lambda_param) * max_sim_to_selected

            if mmr_score > best_score:
                best_score = mmr_score
                best_idx = idx

        if best_idx is None:
            break
        selected.append(best_idx)
        remaining.remove(best_idx)

    return [
        {**candidates[i], "mmr_score": _cosine_similarity(query_embedding, candidates[i]["embedding"])}
        for i in selected
    ]


def rerank_rrf(
    ranked_lists: list[list[dict]], top_k: int = 5, k: int = 60
) -> list[dict]:
    """
    Reciprocal Rank Fusion — gộp kết quả từ nhiều ranker.

    RRF(d) = Σ 1 / (k + rank_r(d))

    Args:
        ranked_lists: List of ranked result lists (mỗi list từ 1 ranker)
        top_k: Số lượng kết quả cuối cùng
        k: Smoothing constant (default=60, từ paper Cormack et al. 2009)

    Returns:
        List of top_k candidates sorted by RRF score descending.
    """
    if top_k <= 0 or not ranked_lists:
        return []
    if k < 0:
        raise ValueError("k must be non-negative")

    def identity(item: dict) -> Hashable:
        metadata = item.get("metadata") or {}
        return (
            metadata.get("source"),
            metadata.get("chunk_index"),
            item.get("content", ""),
        )

    rrf_scores: dict[Hashable, float] = {}
    content_map: dict[Hashable, dict] = {}
    first_seen: dict[Hashable, int] = {}
    seen_counter = 0

    for ranked_list in ranked_lists:
        seen_in_list: set[Hashable] = set()
        for rank, item in enumerate(ranked_list, 1):
            key = identity(item)
            if key in seen_in_list:
                continue
            seen_in_list.add(key)

            if key not in content_map:
                content_map[key] = {
                    **item,
                    "metadata": dict(item.get("metadata") or {}),
                }
                first_seen[key] = seen_counter
                seen_counter += 1
            rrf_scores[key] = rrf_scores.get(key, 0.0) + 1.0 / (k + rank)

    sorted_keys = sorted(
        rrf_scores,
        key=lambda key: (-rrf_scores[key], first_seen[key]),
    )
    results = []
    for key in sorted_keys[:top_k]:
        result = content_map[key].copy()
        result["metadata"] = dict(content_map[key].get("metadata") or {})
        result["score"] = rrf_scores[key]
        results.append(result)
    return results


# =============================================================================
# Main rerank interface
# =============================================================================

def rerank(
    query: str,
    candidates: list[dict],
    top_k: int = 5,
    method: str = "rrf",  # "cross_encoder" | "mmr" | "rrf"
) -> list[dict]:
    """
    Unified reranking interface.

    Args:
        query: Câu truy vấn
        candidates: Danh sách candidates từ retrieval
        top_k: Số lượng kết quả sau rerank
        method: Phương pháp reranking

    Returns:
        List of top_k reranked candidates.
    """
    if method == "cross_encoder":
        return rerank_cross_encoder(query, candidates, top_k)
    elif method == "mmr":
        raise ValueError(
            "MMR requires query_embedding. Call rerank_mmr() directly."
        )
    elif method == "rrf":
        # Backwards-compatible single-list mode required by the starter API.
        # Hybrid retrieval should call rerank_rrf([dense, sparse]) directly.
        return rerank_rrf([candidates], top_k=top_k)
    else:
        raise ValueError(f"Unknown rerank method: {method}")


if __name__ == "__main__":
    import sys

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    query = "chính sách trả hàng shopee"
    candidates = [
        {"content": "Chính sách trả hàng trong 15 ngày", "score": 0.91, "metadata": {"source": "returns.md", "chunk_index": 0}},
        {"content": "Phương thức thanh toán Shopee", "score": 0.72, "metadata": {"source": "payments.md", "chunk_index": 0}},
        {"content": "Mã voucher SPP123 giảm 50k", "score": 0.65, "metadata": {"source": "vouchers.md", "chunk_index": 0}},
        {"content": "Quy trình đổi trả sản phẩm bị lỗi", "score": 0.88, "metadata": {"source": "returns.md", "chunk_index": 1}},
        {"content": "Hướng dẫn sử dụng ví ShopeePay", "score": 0.45, "metadata": {"source": "payments.md", "chunk_index": 1}},
    ]

    print("=" * 60)
    print(f"Query: {query}")
    print(f"JINA_API_KEY: {'✓ Set' if os.getenv('JINA_API_KEY') else '✗ Not set → RRF fallback'}")
    print("=" * 60)

    # Test unified rerank interface
    results = rerank(query, candidates, top_k=3, method="cross_encoder")
    print("\n[CROSS-ENCODER RERANK]")
    for i, r in enumerate(results, 1):
        score = r.get("rerank_score", r["score"])
        print(f"  {i}. [{score:.3f}] {r['content'][:60]}...")

    # Test RRF directly
    print("\n[RRF DIRECT]")
    rrf_results = rerank_rrf([candidates[:3], candidates[2:]], top_k=3)
    for i, r in enumerate(rrf_results, 1):
        print(f"  {i}. [{r['score']:.3f}] {r['content'][:60]}...")
