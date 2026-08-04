"""
Task 6 — Lexical Search Module (BM25).

BM25 complements semantic search by rewarding exact token matches.  The corpus
is deliberately built with Task 4's loader and splitter so both retrievers rank
the same chunks and can later be fused safely with RRF.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any

from .task4_chunking_indexing import chunk_documents, load_documents


# Keep letters/digits (including Vietnamese Unicode characters) and allow the
# separators commonly found inside voucher/product codes: VOUCHER-20, A.B_12.
_TOKEN_RE = re.compile(r"[^\W_]+(?:[._-][^\W_]+)*", flags=re.UNICODE)

# Public for backwards compatibility with the starter template.  It is filled
# lazily because importing this module should not scan the whole corpus.
CORPUS: list[dict] = []
_BM25_INDEX: Any | None = None


def tokenize(text: str) -> list[str]:
    """Tokenize text for exact, case-insensitive Unicode matching."""
    normalized = unicodedata.normalize("NFC", text or "").casefold()
    return _TOKEN_RE.findall(normalized)


def build_bm25_index(corpus: list[dict]):
    """Build and return a BM25Okapi index for ``corpus``."""
    from rank_bm25 import BM25Okapi

    tokenized_corpus = [tokenize(doc.get("content", "")) for doc in corpus]
    return BM25Okapi(tokenized_corpus)


def _ensure_index() -> tuple[list[dict], Any]:
    """Load Task 4 chunks and build BM25 once per Python process."""
    global CORPUS, _BM25_INDEX

    if _BM25_INDEX is None:
        if not CORPUS:
            CORPUS = chunk_documents(load_documents())
        _BM25_INDEX = build_bm25_index(CORPUS)
    return CORPUS, _BM25_INDEX


def lexical_search(query: str, top_k: int = 10) -> list[dict]:
    """
    Search Task 4 chunks with BM25.

    Only positive-scoring matches are returned. Results are sorted by raw BM25
    score in descending order and keep the original chunk metadata.
    """
    query_tokens = tokenize(query)
    if top_k <= 0 or not query_tokens:
        return []

    corpus, bm25 = _ensure_index()
    if not corpus:
        return []

    scores = bm25.get_scores(query_tokens)
    ranked_indices = sorted(
        range(len(corpus)),
        key=lambda index: (-float(scores[index]), index),
    )

    results = []
    for index in ranked_indices:
        score = float(scores[index])
        if score <= 0:
            break
        document = corpus[index]
        results.append(
            {
                "content": document["content"],
                "score": score,
                "metadata": dict(document.get("metadata", {})),
            }
        )
        if len(results) >= top_k:
            break
    return results


if __name__ == "__main__":
    results = lexical_search("phương thức thanh toán shopee", top_k=5)
    for result in results:
        print(f"[{result['score']:.3f}] {result['content'][:100]}...")
