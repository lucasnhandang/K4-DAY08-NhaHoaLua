"""Task 8 — PageIndex vectorless retrieval and document management."""

from __future__ import annotations

import hashlib
import json
import os
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Iterator

from dotenv import load_dotenv

load_dotenv()

PROJECT_ROOT = Path(__file__).resolve().parent.parent
STANDARDIZED_DIR = PROJECT_ROOT / "data" / "standardized"
PDF_CACHE_DIR = PROJECT_ROOT / "data" / "_tmp_pdf"
DOC_ID_CACHE_PATH = PROJECT_ROOT / "pageindex_doc_ids.json"

UPLOAD_TIMEOUT_SECONDS = 60
RETRIEVAL_TIMEOUT_SECONDS = 60
POLL_INTERVAL_SECONDS = 2
MAX_SEARCH_WORKERS = 4
CACHE_VERSION = 1


def _api_key() -> str:
    """Read the key at call time so tests and shells can update the environment."""
    key = os.getenv("PAGEINDEX_API_KEY", "").strip()
    if not key:
        raise RuntimeError(
            "Thiếu PAGEINDEX_API_KEY. Hãy tạo .env từ .env.example và điền API key."
        )
    return key


def _client():
    from pageindex import PageIndexClient

    return PageIndexClient(api_key=_api_key())


def _empty_cache() -> dict:
    return {"version": CACHE_VERSION, "documents": {}}


def _load_cache() -> dict:
    if not DOC_ID_CACHE_PATH.is_file():
        return _empty_cache()
    try:
        cache = json.loads(DOC_ID_CACHE_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"Cache PageIndex không hợp lệ: {DOC_ID_CACHE_PATH}") from exc
    if not isinstance(cache.get("documents"), dict):
        raise RuntimeError(f"Cache PageIndex thiếu trường documents: {DOC_ID_CACHE_PATH}")
    return cache


def _save_cache(cache: dict) -> None:
    temporary_path = DOC_ID_CACHE_PATH.with_suffix(".json.tmp")
    temporary_path.write_text(
        json.dumps(cache, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    temporary_path.replace(DOC_ID_CACHE_PATH)


def _source_key(source_path: Path) -> str:
    return source_path.relative_to(PROJECT_ROOT).as_posix()


def _source_hash(source_path: Path) -> str:
    return hashlib.sha256(source_path.read_bytes()).hexdigest()


def _find_unicode_font() -> Path:
    windows_dir = Path(os.getenv("WINDIR", "C:/Windows"))
    candidates = [
        windows_dir / "Fonts" / "arial.ttf",
        windows_dir / "Fonts" / "segoeui.ttf",
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
        Path("/System/Library/Fonts/Supplemental/Arial Unicode.ttf"),
        Path("/System/Library/Fonts/Supplemental/Arial.ttf"),
    ]
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    raise FileNotFoundError(
        "Không tìm thấy font Unicode để chuyển Markdown sang PDF. "
        "Hãy cài Arial, Segoe UI hoặc DejaVu Sans."
    )


def _pdf_path(source_path: Path) -> Path:
    relative = source_path.relative_to(STANDARDIZED_DIR).with_suffix("")
    filename = "__".join(relative.parts) + ".pdf"
    return PDF_CACHE_DIR / filename


def _render_markdown_pdf(source_path: Path) -> Path:
    """Render Markdown as a Unicode PDF while preserving heading hierarchy."""
    from fpdf import FPDF

    PDF_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    output_path = _pdf_path(source_path)
    source_digest = _source_hash(source_path)
    digest_path = output_path.with_suffix(".sha256")
    if (
        output_path.is_file()
        and digest_path.is_file()
        and digest_path.read_text(encoding="ascii").strip() == source_digest
    ):
        return output_path

    pdf = FPDF(format="A4")
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.set_title(source_path.stem)
    pdf.set_creator("K4 Day 8 PageIndex uploader")
    pdf.add_page()
    pdf.add_font("Unicode", fname=str(_find_unicode_font()))

    heading_pattern = re.compile(r"^(#{1,6})\s+(.*)$")
    for raw_line in source_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.rstrip()
        heading = heading_pattern.match(line)
        if heading:
            level = len(heading.group(1))
            text = heading.group(2).strip()
            pdf.set_font("Unicode", size=max(12, 20 - level * 2))
            pdf.ln(2)
        else:
            text = line or " "
            pdf.set_font("Unicode", size=10.5)
        pdf.multi_cell(0, 5.5, text=text, new_x="LMARGIN", new_y="NEXT")

    pdf.output(str(output_path))
    digest_path.write_text(source_digest, encoding="ascii")
    return output_path


def upload_documents(force: bool = False) -> dict[str, str]:
    """
    Upload all standardized Markdown documents and wait until retrieval-ready.

    Unchanged sources reuse their cached PageIndex ``doc_id``. ``force=True``
    creates new remote documents but intentionally does not delete the old ones.
    """
    source_paths = sorted(STANDARDIZED_DIR.rglob("*.md"))
    if not source_paths:
        raise RuntimeError(f"Không tìm thấy Markdown trong {STANDARDIZED_DIR}")

    client = _client()
    cache = _load_cache()
    cache["version"] = CACHE_VERSION
    documents = cache.setdefault("documents", {})
    active: dict[str, str] = {}

    # Submit everything first so PageIndex can process documents concurrently.
    for source_path in source_paths:
        source = _source_key(source_path)
        digest = _source_hash(source_path)
        cached = documents.get(source, {})
        if not force and cached.get("sha256") == digest and cached.get("doc_id"):
            active[source] = cached["doc_id"]
            continue

        pdf_path = _render_markdown_pdf(source_path)
        response = client.submit_document(str(pdf_path))
        doc_id = response.get("doc_id") or response.get("id")
        if not doc_id:
            raise RuntimeError(f"PageIndex không trả doc_id cho {source}")
        documents[source] = {
            "sha256": digest,
            "doc_id": doc_id,
            "status": "submitted",
        }
        active[source] = doc_id
        _save_cache(cache)

    deadline = time.monotonic() + UPLOAD_TIMEOUT_SECONDS
    pending = set(active)
    failures: dict[str, str] = {}
    while pending and time.monotonic() < deadline:
        for source in sorted(pending):
            try:
                tree = client.get_tree(active[source])
            except Exception as exc:  # SDK exposes version-specific API errors.
                failures[source] = str(exc)
                pending.remove(source)
                continue

            status = str(tree.get("status", "processing")).lower()
            retrieval_ready = bool(tree.get("retrieval_ready"))
            documents[source]["status"] = status
            if status == "completed" and retrieval_ready:
                documents[source]["status"] = "ready"
                pending.remove(source)
            elif status in {"failed", "error"}:
                failures[source] = str(tree.get("error") or status)
                pending.remove(source)
        _save_cache(cache)
        if pending:
            time.sleep(POLL_INTERVAL_SECONDS)

    if pending:
        for source in pending:
            documents[source]["status"] = "timeout"
        _save_cache(cache)
        failures.update({source: "processing timeout" for source in pending})
    if failures:
        failed_sources = ", ".join(sorted(failures))
        raise RuntimeError(f"PageIndex không xử lý xong các tài liệu: {failed_sources}")

    return dict(sorted(active.items()))


def _iter_relevant_items(value: Any) -> Iterator[dict]:
    """Flatten both current and older nested relevant_contents schemas."""
    if isinstance(value, dict):
        yield value
    elif isinstance(value, list):
        for item in value:
            yield from _iter_relevant_items(item)


def _parse_retrieval(response: dict, source: str, doc_id: str) -> list[dict]:
    parsed = []
    for node in response.get("retrieved_nodes") or []:
        node_title = node.get("title") or node.get("section_title") or ""
        for item in _iter_relevant_items(node.get("relevant_contents") or []):
            content = str(item.get("relevant_content") or item.get("content") or "").strip()
            if not content:
                continue
            parsed.append(
                {
                    "content": content,
                    "metadata": {
                        "source": source,
                        "doc_id": doc_id,
                        "section": item.get("section_title") or node_title,
                        "node_id": item.get("node_id") or node.get("node_id"),
                        "page_index": item.get("page_index") or node.get("page_index"),
                    },
                    "source": "pageindex",
                }
            )
    return parsed


def _query_document(client, source: str, doc_id: str, query: str) -> list[dict]:
    submission = client.submit_query(doc_id=doc_id, query=query, thinking=True)
    retrieval_id = submission.get("retrieval_id") or submission.get("id")
    if not retrieval_id:
        raise RuntimeError(f"PageIndex không trả retrieval_id cho {source}")

    deadline = time.monotonic() + RETRIEVAL_TIMEOUT_SECONDS
    while time.monotonic() < deadline:
        response = client.get_retrieval(retrieval_id)
        status = str(response.get("status", "processing")).lower()
        if status == "completed":
            return _parse_retrieval(response, source, doc_id)
        if status in {"failed", "error"}:
            raise RuntimeError(str(response.get("error") or status))
        time.sleep(POLL_INTERVAL_SECONDS)
    raise TimeoutError(f"PageIndex retrieval timeout cho {source}")


def pageindex_search(query: str, top_k: int = 5) -> list[dict]:
    """Retrieve structural evidence from every cached PageIndex document."""
    if top_k <= 0 or not query.strip():
        return []

    client = _client()
    documents = _load_cache().get("documents", {})
    ready_documents = [
        (source, record["doc_id"])
        for source, record in sorted(documents.items())
        if record.get("doc_id") and record.get("status") == "ready"
    ]
    if not ready_documents:
        raise RuntimeError(
            "Chưa có tài liệu PageIndex sẵn sàng. Hãy chạy "
            "python -m src.task8_pageindex_vectorless để upload trước."
        )

    results_by_source: dict[str, list[dict]] = {}
    failures: dict[str, str] = {}
    worker_count = min(MAX_SEARCH_WORKERS, len(ready_documents))
    with ThreadPoolExecutor(max_workers=worker_count) as executor:
        futures = {
            executor.submit(_query_document, client, source, doc_id, query): source
            for source, doc_id in ready_documents
        }
        for future in as_completed(futures):
            source = futures[future]
            try:
                results_by_source[source] = future.result()
            except Exception as exc:
                failures[source] = str(exc)

    if not results_by_source and failures:
        failed_sources = ", ".join(sorted(failures))
        raise RuntimeError(f"Tất cả truy vấn PageIndex đều thất bại: {failed_sources}")

    ranked = []
    for source in sorted(results_by_source):
        for local_rank, result in enumerate(results_by_source[source], 1):
            item = result.copy()
            item["metadata"] = dict(result.get("metadata") or {})
            item["score"] = 1.0 / (60 + local_rank)
            ranked.append((local_rank, source, item))
    ranked.sort(key=lambda entry: (entry[0], entry[1]))
    return [entry[2] for entry in ranked[:top_k]]


if __name__ == "__main__":
    import sys

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    print("Uploading and checking PageIndex documents...")
    uploaded = upload_documents()
    print(f"Ready: {len(uploaded)} documents")

    query = "Tóm tắt toàn bộ quy trình khiếu nại trả hàng cho người bán"
    print(f"\nQuery: {query}")
    for result in pageindex_search(query, top_k=3):
        print(f"[{result['score']:.4f}] {result['content'][:120]}...")
