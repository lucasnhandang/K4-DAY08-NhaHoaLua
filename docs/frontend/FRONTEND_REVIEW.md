# Frontend Review — E-commerce Support RAG Chatbot

Phạm vi: `app.py` (Streamlit chatbot UI) + `src/task10_generation.py` (Generation có Citation).
Role phụ trách: **Role 4 — Frontend & Chatbot Developer** (Phương Án B, nhóm 5 người).

---

## 1. Tổng quan

Chatbot Streamlit hỏi-đáp chính sách thương mại điện tử (đổi trả, thanh toán, quy định người bán...),
trả lời có trích dẫn nguồn, hỗ trợ hội thoại nhiều lượt (follow-up). Giao diện được thiết kế lại theo
[`design/stitch_streamlit_ui_enhancement/DESIGN.md`](../../design/stitch_streamlit_ui_enhancement/DESIGN.md)
— dark mode, tông Indigo/Violet, glassmorphism.

## 2. Luồng dữ liệu

```
app.py (Streamlit UI)
  │  query, top_k (slider), chat_history (session_state.messages)
  ▼
generate_with_citation()        [src/task10_generation.py]
  │
  ├─ retrieve(query, top_k)     [src/task9_retrieval_pipeline.py — Role 1, CHƯA xong]
  │     └─ semantic_search + lexical_search + rerank_rrf + PageIndex fallback
  │
  ├─ reorder_for_llm(chunks)    chống "lost in the middle": best → worst → 2nd-best
  ├─ format_context(chunks)     gắn nhãn [Document i | Source | Type] cho từng chunk
  └─ gọi OpenRouter (LLM_MODEL) với system prompt bắt buộc trích dẫn
        │
        ▼
  {'answer', 'sources', 'retrieval_source'}
        │
        ▼
  app.py hiển thị: câu trả lời + badge nguồn (hybrid/pageindex) + mini-card nguồn có highlight
```

Schema chunk cố định xuyên suốt pipeline:
```python
{'content': str, 'score': float, 'metadata': {'source': str, 'type': str, 'chunk_index': int}, 'source': str}
```

## 3. Đã hoàn thành

### Task 10 — `src/task10_generation.py`
| Hàm | Trạng thái | Ghi chú |
|---|---|---|
| `reorder_for_llm()` | ✅ | `front = chunks[::2]`, `back đảo = chunks[1::2][::-1]` |
| `format_context()` | ✅ | Nhãn `[Document i \| Source: ... \| Type: ...]` |
| `generate_with_citation()` | ✅ | Gọi OpenRouter, hỗ trợ `chat_history` (tối đa `MAX_HISTORY_TURNS=3` lượt gần nhất) |

Model dùng: `inclusionai/ling-3.0-flash:free` (OpenRouter, free tier — không tốn credit).

### `app.py` — Streamlit UI
- Sidebar: brand header, 5 câu hỏi gợi ý dạng chip, slider `top_k` (3-10), nút **"➕ Cuộc trò chuyện mới"**.
- Header: status pill tự động (🟢 SẴN SÀNG / 🟡 CHƯA CÓ API KEY dựa trên `OPENROUTER_API_KEY`).
- Chat area: bong bóng chat bo góc, avatar riêng user/assistant, khung cảnh báo lỗi viền đỏ trái.
- Mỗi câu trả lời kèm:
  - **Badge nguồn retrieval** (🟢 Hybrid Search / 🟠 PageIndex Fallback) — đọc field `retrieval_source` trước đây bị bỏ qua.
  - **Mini-card nguồn trích dẫn** — icon theo loại tài liệu (📄 legal / 📰 news), score, và **highlight từ khoá** trùng khớp câu hỏi trong đoạn trích.
- **Conversation memory**: lịch sử hội thoại (`session_state.messages`) được truyền vào `generate_with_citation(..., chat_history=...)` — LLM hiểu được câu hỏi follow-up kiểu "trong số đó, cái nào...".
- Theme: `.streamlit/config.toml` + CSS injected tái tạo bản design (font Inter/JetBrains Mono, glass panel, rounded corners, floating input).

### Đã fix chung (không riêng frontend nhưng cần để chạy được)
- `requirements.txt`: gỡ xung đột dependency `ragas==0.1.21` (ghim `langchain-core<0.3`) → nâng lên `ragas>=0.2.15,<0.5.0`.

## 4. Đã kiểm chứng bằng test thật (không chỉ đọc code)

```powershell
python -m pytest tests/test_individual.py -k Task10 -v
```
```
test_format_context_includes_source   PASSED
test_reorder_function_exists          PASSED
test_generate_returns_dict_with_answer SKIPPED   # phụ thuộc retrieve() — Task 9 chưa xong
```

- Test bằng **mock `retrieve()`** (không chờ Task 9): xác nhận `reorder_for_llm`, `format_context`,
  và cả lệnh gọi LLM thật (OpenRouter) hoạt động đúng, trả lời có trích dẫn `[payment-methods.md]`.
- Test **conversation memory** bằng 2 lượt hỏi liên tiếp: câu hỏi follow-up "Trong số đó, cái nào phổ biến nhất?"
  được LLM hiểu đúng nhờ `chat_history`, đồng thời vẫn từ chối bịa đặt khi context không có dữ liệu (đúng luật
  chống hallucination trong `SYSTEM_PROMPT`).
- Chạy `streamlit run app.py` thật + chụp màn hình bằng Playwright, so khớp với `screen.png` gốc trong bản design
  (xem ảnh bên dưới).
- `pytest tests/test_individual.py -v` toàn bộ: **18 passed, 17 skipped, 0 failed** (skip là do phụ thuộc
  Task 5-9 của các role khác, không phải lỗi).

### Ảnh chụp thực tế

| Màn hình chính | Trạng thái chờ Task 9 |
|---|---|
| ![Home](screenshots/01_home.png) | ![Chat pending](screenshots/02_chat_pending_task9.png) |

## 5. Giới hạn hiện tại / việc còn lại

- **Chưa test được câu trả lời thật end-to-end** — `retrieve()` (Task 9, Role 1) vẫn `NotImplementedError`
  trên cả `main`. Đã xác minh Task 4/5/6/8 team đã merge xong, Task 7 gần xong (còn 3 `NotImplementedError`
  nhỏ). Khi Task 9 xong, `app.py` sẽ chạy được ngay không cần sửa gì thêm (đã verify bằng mock).
- **Deploy online** (bonus 4đ) — chưa làm, cần tài khoản Streamlit Community Cloud / HF Spaces.
- **Kiến trúc diagram cho `group_project/README.md`** (3đ, việc chung) — chưa vẽ.

## 6. Cách chạy Frontend

### Bước 1 — Setup môi trường (nếu chưa làm ở CP0)
```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### Bước 2 — Khai báo API key
```powershell
copy .env.example .env
```
Mở `.env`, điền tối thiểu:
```
OPENROUTER_API_KEY=sk-or-v1-...
```
(Lấy free tại https://openrouter.ai — không bắt buộc trả phí, có model `:free`.)

### Bước 3 — (Khuyến khích) tải trước embedding model
Tránh Streamlit bị treo lúc demo do tự tải model ~2.2GB giữa chừng:
```powershell
python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('BAAI/bge-m3')"
```

### Bước 4 — Chạy app
```powershell
streamlit run app.py
```
Mở trình duyệt tại `http://localhost:8501`.

### Trạng thái mong đợi hiện tại
Vì Task 9 chưa xong, mọi câu hỏi sẽ trả về khung cảnh báo màu đỏ **"Task 10 chưa được implement"**
(thực chất là lỗi từ `retrieve()` của Task 9, không phải lỗi UI) — đây là hành vi đúng theo thiết kế,
không phải bug. Khi Role 1 hoàn thành Task 9, chạy lại `streamlit run app.py` sẽ thấy câu trả lời thật
kèm citation, badge nguồn, và mini-card trích dẫn.

### Test nhanh không cần chờ Task 9 (dùng mock)
Xem hướng dẫn mock trong quá trình phát triển ở phần "Đã kiểm chứng" phía trên — có thể tự viết script
tương tự dùng `unittest.mock.patch("src.task10_generation.retrieve", return_value=<list chunk giả>)`
để test `generate_with_citation()` mà không cần Task 9.
