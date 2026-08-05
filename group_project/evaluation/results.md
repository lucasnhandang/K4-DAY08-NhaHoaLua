# RAG Evaluation Results

## Framework

RAGAS 0.1.21 với 20 câu hỏi trong `golden_dataset.json`.

## Overall Scores

| Metric | hybrid_rerank | dense_only | Δ |
|---|---:|---:|---:|
| Faithfulness | 0.879 | 0.913 | -0.034 |
| Answer Relevance | 0.717 | 0.715 | 0.002 |
| Context Recall | 1.000 | 1.000 | 0.000 |
| Context Precision | 0.990 | 0.990 | -0.000 |
| Average | 0.896 | 0.905 | -0.008 |

## A/B Comparison

Cấu hình **dense_only** có điểm trung bình cao hơn trên bộ kiểm thử.

## Worst Performers (Bottom 3)

| # | Question | Faithfulness | Relevance | Recall | Precision |
|---:|---|---:|---:|---:|---:|
| 1 | Khi đơn ở trạng thái Chờ lấy hàng, người mua hủy đơn như thế nào? | 0.667 | 0.000 | 1.000 | 1.000 |
| 2 | Khi tự sắp xếp trả hàng cho sản phẩm Shopee Mall, người mua nhận lại phí vận chuyển thế nào? | 0.000 | 0.737 | 1.000 | 1.000 |
| 3 | Tiền hoàn của đơn thanh toán bằng thẻ tín dụng hoặc ghi nợ được trả về đâu và mất bao lâu? | 1.000 | 0.000 | 1.000 | 1.000 |

## Recommendations

1. Kiểm tra các câu có Context Recall thấp và bổ sung query expansion hoặc điều chỉnh `top_k`.
2. Với Context Precision thấp, hiệu chỉnh BM25/RRF và reranker để loại chunk nhiễu.
3. Với Faithfulness thấp, siết system prompt và yêu cầu từ chối khi context không đủ bằng chứng.

## Reproduction

```powershell
.\.venv\Scripts\python.exe -m group_project.evaluation.eval_pipeline
```
