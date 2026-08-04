# RAG Evaluation Results

## Framework sử dụng

Nhóm sử dụng **RAGAS 0.1.21** để đánh giá pipeline RAG trên 4 trục:

- **Faithfulness:** câu trả lời có bám sát context được truy xuất hay không.
- **Answer Relevance:** câu trả lời có trực tiếp giải quyết câu hỏi hay không.
- **Context Recall:** context có bao phủ đủ thông tin trong đáp án chuẩn hay không.
- **Context Precision:** các context được đưa vào có thực sự liên quan hay không.

Bộ kiểm thử hiện tại gồm **15 câu hỏi** trong `golden_dataset.json`. LLM judge dùng
`openai/gpt-4o-mini` qua OpenRouter; embedding judge dùng `BAAI/bge-m3` chạy local.

## Cấu hình A/B

| Cấu hình | Retrieval | Reranking | PageIndex fallback |
|---|---|---|---|
| `hybrid_rerank` | Semantic + BM25, hợp nhất bằng RRF | Bật | Bật khi cosine gốc `< 0.48` |
| `dense_only` | Chỉ semantic search | Tắt | Tắt |

Hai cấu hình sử dụng cùng golden dataset, cùng model generation và cùng bộ RAGAS
metrics để bảo đảm phép so sánh nhất quán.

## Overall Scores

| Metric | `hybrid_rerank` | `dense_only` | Δ (Hybrid − Dense) |
|---|---:|---:|---:|
| Faithfulness | 0.893 | 0.887 | +0.006 |
| Answer Relevance | 0.700 | 0.706 | -0.006 |
| Context Recall | 1.000 | 1.000 | 0.000 |
| Context Precision | 0.987 | 0.987 | 0.000 |
| **Average** | **0.895** | **0.895** | **0.000** |

## Phân tích A/B

Hai cấu hình **hòa nhau ở điểm trung bình sau khi làm tròn 3 chữ số**. Vì vậy
không có đủ chênh lệch để kết luận một cấu hình thắng tuyệt đối.

`hybrid_rerank` có Faithfulness cao hơn khoảng 0.006, cho thấy việc kết hợp semantic
với BM25/RRF có thể giúp câu trả lời bám evidence tốt hơn một chút. Ngược lại,
`dense_only` có Answer Relevance cao hơn khoảng 0.006. Context Recall và Context
Precision gần như tối đa và không khác nhau, nên điểm nghẽn chính nằm ở bước
generation/answer formulation, không phải khả năng tìm thấy evidence.

## Worst Performers (Bottom 3 của `hybrid_rerank`)

| # | Question | Faithfulness | Relevance | Recall | Precision | Failure stage | Root-cause hypothesis |
|---:|---|---:|---:|---:|---:|---|---|
| 1 | Khi tự sắp xếp trả hàng cho sản phẩm Shopee Mall, người mua nhận lại phí vận chuyển thế nào? | 0.000 | 0.725 | 1.000 | 1.000 | Generation | Context đã chứa đủ evidence nhưng câu trả lời có chi tiết không được context hỗ trợ hoặc diễn giải sai cơ chế hoàn vào Số dư Tài khoản Shopee trong 3–5 ngày làm việc. |
| 2 | Tiền hoàn của đơn thanh toán bằng thẻ tín dụng hoặc ghi nợ được trả về đâu và mất bao lâu? | 1.000 | 0.000 | 1.000 | 1.000 | Answer formulation | Câu trả lời bám context nhưng không trả lời trực tiếp đủ hai ý bắt buộc: hoàn về đúng thẻ và thời gian 7–14 ngày làm việc. |
| 3 | Thực phẩm tươi sống hoặc hàng cần bảo quản đặc biệt nên giao bằng hình thức nào? | 1.000 | 0.000 | 1.000 | 1.000 | Answer formulation | Evidence được truy xuất đầy đủ nhưng câu trả lời có thể không nêu trực tiếp “Hỏa Tốc” hoặc bị judge đánh giá lệch trọng tâm câu hỏi. |

Các root cause trên là giả thuyết dựa trên pattern metric. Muốn xác nhận hoàn toàn cần
lưu thêm answer và contexts của từng case vào artifact đánh giá.

## Recommendations

### 1. Siết prompt cho câu hỏi nhiều ý

**Action:** yêu cầu model tách từng điều kiện trong câu hỏi và trả lời đủ từng ý trước
khi kết thúc; đặc biệt với các câu hỏi dạng “ở đâu và bao lâu”.

**Expected impact:** tăng Answer Relevance mà không làm giảm Faithfulness.

### 2. Kiểm tra grounding trước khi trả lời

**Action:** thêm bước tự kiểm tra rằng mọi con số, thời hạn và kênh hoàn tiền đều xuất
hiện trong context; nếu thiếu thì trả lời không thể xác minh.

**Expected impact:** giảm lỗi hallucination ở case Shopee Mall và tăng Faithfulness.

### 3. Lưu artifact theo từng test case

**Action:** xuất question, generated answer, retrieved contexts, retrieval source và 4
metric scores ra JSON/CSV bên cạnh báo cáo Markdown.

**Expected impact:** giúp phân biệt lỗi retrieval với lỗi generation và làm cho kết quả
có thể audit/reproduce.

### 4. Hiệu chỉnh reranker API

**Action:** thay `JINA_API_KEY` đang trả HTTP 403 hoặc để trống key để dùng RRF local
một cách rõ ràng.

**Expected impact:** tránh 20 request thất bại và giảm đáng kể thời gian chạy benchmark.

## Hạn chế và trạng thái tái chạy

- Dataset hiện có 15 câu, không phải 20 câu như mô tả cũ.
- RAGAS dùng LLM judge nên điểm có thể dao động nhẹ giữa các lần chạy.
- Lần tái chạy gần nhất không được dùng để thay thế bảng điểm trên vì bị dừng ở cấu
  hình `dense_only` do OpenRouter trả HTTP 402 (không đủ credit/max-token budget).
- Jina Reranker trả HTTP 403 trong lần tái chạy; pipeline đã tự fallback về RRF.
- Các giá trị trong bảng được giữ ở độ chính xác 3 chữ số; delta được tính từ các giá
  trị đang hiển thị.

## Reproduction

Chạy thử ít case trước để kiểm tra key và quota:

```powershell
$env:PYTHONIOENCODING="utf-8"
$env:JINA_API_KEY=""
.\.venv\Scripts\python.exe -m group_project.evaluation.eval_pipeline --limit 2
```

Chạy toàn bộ 15 câu cho hai cấu hình A/B:

```powershell
$env:PYTHONIOENCODING="utf-8"
$env:JINA_API_KEY=""
.\.venv\Scripts\python.exe -m group_project.evaluation.eval_pipeline
```

Khi hoàn tất, script sẽ tự ghi lại báo cáo này từ kết quả RAGAS mới.
