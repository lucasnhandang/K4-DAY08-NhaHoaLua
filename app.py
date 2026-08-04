"""
RAG Chatbot — E-commerce Support (Starter Template)
Streamlit app kết nối RAG Retrieval (Task 9) và Generation (Task 10).

Giao diện theo design/stitch_streamlit_ui_enhancement/DESIGN.md
(dark mode, glassmorphism, tông Indigo/Violet).

Chạy:
    streamlit run app.py
"""

import html
import os
import re
import sys
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

load_dotenv()

# Thêm project root vào sys.path để import các task từ src/
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

# =============================================================================
# HELPERS — highlight từ khoá, badge nguồn retrieval, render sources
# =============================================================================

STOPWORDS = {
    "là", "của", "và", "có", "cho", "được", "gì", "như", "thế", "nào",
    "khi", "tôi", "bạn", "sao", "làm", "để", "về", "này", "đó", "một",
    "các", "những", "the", "a", "an", "is", "of", "to", "in", "on",
}

DOC_TYPE_ICONS = {"legal": "📄", "news": "📰"}


def highlight_keywords(text: str, query: str) -> str:
    """Bọc <mark> quanh từ khoá của query xuất hiện trong đoạn trích (đã escape HTML)."""
    escaped = html.escape(text)
    keywords = [
        w for w in re.findall(r"\w+", query.lower(), flags=re.UNICODE)
        if len(w) > 1 and w not in STOPWORDS
    ]
    if not keywords:
        return escaped
    pattern = re.compile(
        "|".join(re.escape(k) for k in sorted(set(keywords), key=len, reverse=True)),
        re.IGNORECASE,
    )
    return pattern.sub(lambda m: f"<mark>{m.group(0)}</mark>", escaped)


def error_notice(message: str) -> str:
    return f'<div class="error-notice">⚠️&nbsp; {message}</div>'


def retrieval_badge(source: str) -> str:
    if source == "pageindex":
        return (
            '<div class="retrieval-badge badge-warn">🟠 <strong>PageIndex Fallback</strong>'
            " — điểm tương đồng vector thấp, đã chuyển sang tìm kiếm không vector</div>"
        )
    return (
        '<div class="retrieval-badge badge-ok">🟢 <strong>Hybrid Search</strong>'
        " (Semantic + BM25 + RRF Rerank)</div>"
    )


def render_sources(sources: list[dict], query: str) -> None:
    with st.expander(f"📚 Nguồn tham khảo ({len(sources)} chunks)"):
        for i, src in enumerate(sources, 1):
            meta = src.get("metadata", {})
            source_name = html.escape(meta.get("source", "Unknown"))
            doc_type = meta.get("type", "unknown")
            icon = DOC_TYPE_ICONS.get(doc_type, "🔗")
            score = src.get("score", 0)
            snippet = highlight_keywords(src.get("content", "")[:300] + "...", query)
            st.markdown(
                f'<div class="source-card">'
                f'<div class="source-card-header">{icon} <strong>[{i}] {source_name}</strong> '
                f'<span class="source-chip">{doc_type}</span>'
                f'<span class="source-score">score {score:.4f}</span></div>'
                f'<div class="source-card-body">{snippet}</div>'
                f"</div>",
                unsafe_allow_html=True,
            )


# =============================================================================
# PAGE CONFIG
# =============================================================================

st.set_page_config(
    page_title="E-commerce Support RAG Chatbot",
    page_icon="🛒",
    layout="wide",
    initial_sidebar_state="expanded",
)

# =============================================================================
# THEME CSS — tái tạo design/stitch_streamlit_ui_enhancement (dark, glassmorphism)
# =============================================================================

st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

html, body, [data-testid="stApp"] {
    font-family: 'Inter', -apple-system, 'Segoe UI', sans-serif !important;
}
code, .source-chip, .source-score, .status-pill {
    font-family: 'JetBrains Mono', monospace !important;
}

[data-testid="stSidebar"] {
    background: #131b2e !important;
    border-right: 1px solid #46455440;
}

[data-testid="stSidebar"] [data-testid="stBaseButton-secondary"] {
    background: #171f33 !important;
    border: 1px solid #46455433 !important;
    color: #c7c4d7 !important;
    border-radius: 10px !important;
    justify-content: flex-start !important;
    text-align: left !important;
}
[data-testid="stSidebar"] [data-testid="stBaseButton-secondary"]:hover {
    background: #2d3449 !important;
    color: #c0c1ff !important;
    border-color: #c0c1ff55 !important;
}

[data-testid="stSidebar"] [data-testid="stBaseButton-primary"] {
    background: #8083ff !important;
    color: #0d0096 !important;
    border-radius: 999px !important;
    font-weight: 600 !important;
    border: none !important;
}
[data-testid="stSidebar"] [data-testid="stBaseButton-primary"]:hover {
    background: #c0c1ff !important;
}

[data-testid="stChatMessage"] { margin-bottom: 4px; }

[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) [data-testid="stChatMessageContent"] {
    background: #222a3d !important;
    border: 1px solid #46455422;
    border-radius: 16px 16px 4px 16px !important;
    padding: 14px 18px !important;
}
[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarAssistant"]) [data-testid="stChatMessageContent"] {
    background: rgba(45, 52, 73, 0.45) !important;
    backdrop-filter: blur(12px);
    -webkit-backdrop-filter: blur(12px);
    border: 1px solid #46455422;
    border-radius: 16px 16px 16px 4px !important;
    padding: 14px 18px !important;
}
[data-testid="stChatMessageAvatarUser"] { background: #571bc1 !important; }
[data-testid="stChatMessageAvatarAssistant"] {
    background: #2d3449 !important;
    box-shadow: 0 0 14px #c0c1ff33;
}

[data-testid="stChatInput"] {
    background: rgba(45, 52, 73, 0.5) !important;
    backdrop-filter: blur(12px);
    -webkit-backdrop-filter: blur(12px);
    border: 1px solid #46455433 !important;
    border-radius: 20px !important;
    box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.4);
}
[data-testid="stChatInputSubmitButton"] {
    background: #8083ff !important;
    border-radius: 12px !important;
}

[data-testid="stExpander"] {
    background: #171f33 !important;
    border: 1px solid #46455433 !important;
    border-radius: 12px !important;
}

.source-card {
    background: #171f33;
    border: 1px solid #46455433;
    border-radius: 12px;
    padding: 10px 14px;
    margin-bottom: 10px;
}
.source-card-header {
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    gap: 8px;
    font-size: 0.9em;
    margin-bottom: 6px;
}
.source-chip {
    background: #2d3449;
    color: #c7c4d7;
    padding: 1px 8px;
    border-radius: 999px;
    font-size: 0.75em;
}
.source-score {
    color: #c0c1ff;
    font-size: 0.8em;
    margin-left: auto;
}
.source-card-body {
    font-size: 0.85em;
    line-height: 1.5;
    color: #c7c4d7;
}
mark {
    background: rgba(253, 224, 71, 0.35);
    color: #dae2fd;
    padding: 0 3px;
    border-radius: 4px;
}

.retrieval-badge {
    display: inline-block;
    padding: 4px 12px;
    border-radius: 999px;
    font-size: 0.85em;
    margin: 6px 0 10px 0;
}
.badge-ok { background: rgba(78, 222, 163, 0.15); color: #4edea3; border: 1px solid #4edea344; }
.badge-warn { background: rgba(255, 180, 171, 0.15); color: #ffb4ab; border: 1px solid #ffb4ab44; }

.status-pill {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 4px 12px;
    border-radius: 999px;
    font-size: 0.75em;
    float: right;
    margin-top: 10px;
}
.status-ready { background: rgba(78, 222, 163, 0.12); color: #4edea3; border: 1px solid #4edea344; }
.status-warn { background: rgba(255, 180, 171, 0.12); color: #ffb4ab; border: 1px solid #ffb4ab44; }

.error-notice {
    border-left: 4px solid #ffb4ab;
    background: rgba(255, 180, 171, 0.06);
    padding: 8px 12px;
    border-radius: 4px;
}
.error-notice strong { color: #ffb4ab; }
.error-notice code {
    background: #171f33;
    color: #4edea3;
    padding: 2px 6px;
    border-radius: 4px;
    border: 1px solid #46455433;
}
</style>
""",
    unsafe_allow_html=True,
)

# =============================================================================
# SIDEBAR — INFO & SETTINGS
# =============================================================================

with st.sidebar:
    st.title("🛒 E-commerce Support RAG")
    st.caption("Trợ lý hỏi đáp về chính sách thương mại điện tử và hỗ trợ khách hàng (đổi trả, thanh toán, bảo mật, người bán)")

    st.divider()

    st.subheader("💡 Câu hỏi gợi ý")
    suggestions = [
        "Thời hạn yêu cầu trả hàng/hoàn tiền là bao lâu?",
        "Shopee hỗ trợ những phương thức thanh toán nào?",
        "Làm sao để đổi phương thức thanh toán đơn hàng?",
        "Quy định về đăng bán sản phẩm cho người bán?",
        "Cách mua hàng trên Shopee của quốc gia khác?",
    ]
    for s in suggestions:
        if st.button(s, use_container_width=True, key=f"sug_{s[:20]}"):
            st.session_state["pending_query"] = s

    st.divider()
    st.subheader("⚙️ Thiết lập")
    top_k = st.slider("Số chunks retrieval (top_k)", 3, 10, 5)

    st.divider()
    st.caption("**Kiến trúc hệ thống:**")
    st.caption("Hybrid Retrieval (Semantic + BM25) → RRF Rerank → PageIndex Fallback → LLM Generation có Citation")

    st.divider()
    if st.button("➕ Cuộc trò chuyện mới", use_container_width=True, type="primary"):
        st.session_state.messages = []
        st.rerun()

# =============================================================================
# SESSION STATE
# =============================================================================

if "messages" not in st.session_state:
    st.session_state.messages = []
if "pending_query" not in st.session_state:
    st.session_state.pending_query = None

# =============================================================================
# MAIN CHAT AREA
# =============================================================================

title_col, status_col = st.columns([5, 2])
with title_col:
    st.title("🛒 E-commerce Support RAG Chatbot")
    st.caption("Hệ thống hỏi đáp chính sách e-commerce và trợ giúp khách hàng")
with status_col:
    # Task 10 hiện gọi OpenRouter trực tiếp, vì vậy OPENAI_API_KEY không đủ để
    # đánh dấu pipeline generation là sẵn sàng.
    api_ready = bool(os.getenv("OPENROUTER_API_KEY", "").strip())
    if api_ready:
        st.markdown('<div class="status-pill status-ready">🟢 SẴN SÀNG</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="status-pill status-warn">🟡 CHƯA CÓ OPENROUTER KEY</div>', unsafe_allow_html=True)

# Hiển thị lịch sử chat
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        if msg["role"] == "assistant" and msg.get("is_error"):
            st.markdown(error_notice(msg["content"]), unsafe_allow_html=True)
        else:
            st.markdown(msg["content"])
        if msg["role"] == "assistant":
            if msg.get("retrieval_source"):
                st.markdown(retrieval_badge(msg["retrieval_source"]), unsafe_allow_html=True)
            if msg.get("sources"):
                render_sources(msg["sources"], msg.get("query", ""))

# =============================================================================
# QUERY HANDLING
# =============================================================================

user_input = st.chat_input("Nhập câu hỏi của bạn về chính sách/hỗ trợ e-commerce...")
query = user_input or st.session_state.pending_query

if query:
    st.session_state.pending_query = None

    # Lịch sử hội thoại trước đó (chưa gồm câu hỏi vừa hỏi) để truyền cho Task 10 làm chat_history
    chat_history = [
        {"role": m["role"], "content": m["content"]}
        for m in st.session_state.messages
        if not m.get("is_error")
    ]

    # Hiển thị câu hỏi của user
    st.session_state.messages.append({"role": "user", "content": query})
    with st.chat_message("user"):
        st.markdown(query)

    # Sinh câu trả lời từ RAG Pipeline
    with st.chat_message("assistant"):
        with st.spinner("Đang tìm kiếm tài liệu và tổng hợp câu trả lời..."):
            try:
                from src.task10_generation import generate_with_citation
                response = generate_with_citation(query, top_k=top_k, chat_history=chat_history)
                answer = response.get("answer", "Chưa thể trả lời.")
                sources = response.get("sources", [])
                retrieval_source = response.get("retrieval_source")

                is_error = False
            except NotImplementedError:
                answer = (
                    "<strong>Task 10 chưa được implement.</strong> Hãy hoàn thành "
                    "<code>src/task10_generation.py</code> để kết nối pipeline vào UI!"
                )
                sources = []
                retrieval_source = None
                is_error = True
            except Exception as e:
                answer = f"<strong>Lỗi khi chạy RAG Pipeline:</strong> {html.escape(str(e))}"
                sources = []
                retrieval_source = None
                is_error = True

            if is_error:
                st.markdown(error_notice(answer), unsafe_allow_html=True)
            else:
                st.markdown(answer)

            if retrieval_source:
                st.markdown(retrieval_badge(retrieval_source), unsafe_allow_html=True)

            if sources:
                render_sources(sources, query)

    st.session_state.messages.append({
        "role": "assistant",
        "content": answer,
        "sources": sources,
        "query": query,
        "retrieval_source": retrieval_source,
        "is_error": is_error,
    })
