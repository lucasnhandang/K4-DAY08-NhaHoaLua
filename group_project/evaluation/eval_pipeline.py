"""RAGAS evaluation and A/B reporting for the e-commerce RAG pipeline.

The evaluator expects a pipeline callable (or an object exposing
``generate_with_citation``) that returns::

    {"answer": str, "sources": [{"content": str, ...}, ...]}

RAGAS is imported lazily, so dataset validation and report formatting can be
tested without installing the relatively heavy evaluation dependencies.
"""

from __future__ import annotations

import argparse
import inspect
import json
import math
import os
from pathlib import Path
from statistics import mean
from typing import Any, Callable, Mapping

from dotenv import load_dotenv

load_dotenv()


GOLDEN_DATASET_PATH = Path(__file__).with_name("golden_dataset.json")
RESULTS_PATH = Path(__file__).with_name("results.md")
REQUIRED_FIELDS = {"question", "expected_answer", "expected_context"}
METRICS = ("faithfulness", "answer_relevancy", "context_recall", "context_precision")
METRIC_LABELS = {
    "faithfulness": "Faithfulness",
    "answer_relevancy": "Answer Relevance",
    "context_recall": "Context Recall",
    "context_precision": "Context Precision",
}


def load_golden_dataset(path: Path = GOLDEN_DATASET_PATH) -> list[dict]:
    """Load and validate the golden Q&A dataset."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise FileNotFoundError(f"Golden dataset not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON in {path}: {exc}") from exc

    if not isinstance(data, list) or not data:
        raise ValueError("Golden dataset must be a non-empty JSON list")
    questions: set[str] = set()
    for index, item in enumerate(data):
        if not isinstance(item, dict) or not REQUIRED_FIELDS.issubset(item):
            raise ValueError(f"Item {index} must contain {sorted(REQUIRED_FIELDS)}")
        for field in REQUIRED_FIELDS:
            if not isinstance(item[field], str) or not item[field].strip():
                raise ValueError(f"Item {index}.{field} must be a non-empty string")
        normalized_question = item["question"].strip().casefold()
        if normalized_question in questions:
            raise ValueError(f"Duplicate question at item {index}: {item['question']}")
        questions.add(normalized_question)
    return data


def _pipeline_callable(pipeline: Any) -> Callable[..., dict]:
    target = getattr(pipeline, "generate_with_citation", pipeline)
    if not callable(target):
        raise TypeError("rag_pipeline must be callable or expose generate_with_citation()")
    return target


def _invoke_pipeline(pipeline: Any, question: str, config: Mapping[str, Any] | None = None) -> dict:
    """Call a pipeline while passing only configuration arguments it supports."""
    target = _pipeline_callable(pipeline)
    signature = inspect.signature(target)
    config = dict(config or {})
    accepts_kwargs = any(
        parameter.kind == inspect.Parameter.VAR_KEYWORD
        for parameter in signature.parameters.values()
    )
    kwargs = config if accepts_kwargs else {
        key: value for key, value in config.items() if key in signature.parameters
    }
    unsupported = set(config) - set(kwargs)
    if unsupported:
        raise TypeError(
            "Pipeline does not support A/B parameters: " + ", ".join(sorted(unsupported))
        )

    result = target(question, **kwargs)
    if not isinstance(result, dict):
        raise TypeError("Pipeline result must be a dictionary")
    answer = result.get("answer")
    sources = result.get("sources")
    if not isinstance(answer, str) or not answer.strip():
        raise ValueError("Pipeline result must contain a non-empty string 'answer'")
    if not isinstance(sources, list):
        raise ValueError("Pipeline result must contain a list 'sources'")
    for index, source in enumerate(sources):
        if not isinstance(source, dict) or not isinstance(source.get("content"), str):
            raise ValueError(f"Source {index} must contain string field 'content'")
    return result


def collect_evaluation_data(
    rag_pipeline: Any,
    golden_dataset: list[dict],
    config: Mapping[str, Any] | None = None,
) -> dict[str, list]:
    """Run the RAG pipeline and create the columns expected by RAGAS 0.1.x."""
    data: dict[str, list] = {
        "question": [], "answer": [], "contexts": [], "ground_truth": []
    }
    for number, item in enumerate(golden_dataset, 1):
        # Keep console progress ASCII-only because some Windows terminals still
        # default to cp1252 and cannot print Vietnamese characters.
        print(f"[{number}/{len(golden_dataset)}] Evaluating case")
        result = _invoke_pipeline(rag_pipeline, item["question"], config)
        data["question"].append(item["question"])
        data["answer"].append(result["answer"])
        data["contexts"].append([source["content"] for source in result["sources"]])
        data["ground_truth"].append(item["expected_answer"])
    return data


def _finite_float(value: Any) -> float | None:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if math.isfinite(result) else None


def _normalise_ragas_result(result: Any, config_name: str) -> dict:
    frame = result.to_pandas()
    rows: list[dict] = []
    for record in frame.to_dict(orient="records"):
        row = {
            "question": str(record.get("question", "")),
            "answer": str(record.get("answer", "")),
        }
        row.update({metric: _finite_float(record.get(metric)) for metric in METRICS})
        rows.append(row)

    overall = {}
    for metric in METRICS:
        values = [row[metric] for row in rows if row[metric] is not None]
        overall[metric] = mean(values) if values else None
    valid_overall = [value for value in overall.values() if value is not None]
    overall["average"] = mean(valid_overall) if valid_overall else None
    return {"framework": "RAGAS", "config": config_name, "overall": overall, "rows": rows}


def _build_ragas_judges() -> tuple[Any, Any]:
    """Create the LLM judge and local embedding model used by RAGAS.

    The application already uses OpenRouter for generation, so the evaluator
    uses the same key for its LLM calls. Answer relevancy also needs embeddings;
    keeping those local makes the evaluation independent from an embedding API.
    """
    api_key = (os.getenv("OPENROUTER_API_KEY") or os.getenv("OPENAI_API_KEY") or "").strip()
    if not api_key:
        raise RuntimeError("Missing OPENROUTER_API_KEY or OPENAI_API_KEY for RAGAS judging")

    from langchain_openai import ChatOpenAI
    from ragas.embeddings import HuggingfaceEmbeddings
    from ragas.llms import LangchainLLMWrapper

    is_openrouter = bool(os.getenv("OPENROUTER_API_KEY"))
    chat_model = ChatOpenAI(
        model=os.getenv("RAGAS_LLM_MODEL", "openai/gpt-4o-mini"),
        api_key=api_key,
        base_url="https://openrouter.ai/api/v1" if is_openrouter else None,
        temperature=0,
    )
    embeddings = HuggingfaceEmbeddings(
        model_name=os.getenv("RAGAS_EMBEDDING_MODEL", "BAAI/bge-m3")
    )
    return LangchainLLMWrapper(chat_model), embeddings


def evaluate_with_ragas(
    rag_pipeline: Any,
    golden_dataset: list[dict],
    config: Mapping[str, Any] | None = None,
    config_name: str = "default",
) -> dict:
    """Run the pipeline and evaluate four standard RAGAS metrics."""
    try:
        from datasets import Dataset
        from ragas import evaluate
        from ragas.metrics import (
            answer_relevancy,
            context_precision,
            context_recall,
            faithfulness,
        )
    except ImportError as exc:
        raise RuntimeError(
            "RAGAS dependencies are missing. Run: pip install "
            "'ragas==0.1.21' 'datasets>=2.14.0' 'langchain-openai>=0.1.0'"
        ) from exc

    eval_data = collect_evaluation_data(rag_pipeline, golden_dataset, config)
    dataset = Dataset.from_dict(eval_data)
    judge_llm, judge_embeddings = _build_ragas_judges()
    result = evaluate(
        dataset,
        metrics=[faithfulness, answer_relevancy, context_recall, context_precision],
        llm=judge_llm,
        embeddings=judge_embeddings,
        raise_exceptions=False,
    )
    return _normalise_ragas_result(result, config_name)


def evaluate_with_deepeval(*_args, **_kwargs):
    """The project selected RAGAS; retained only as an explicit compatibility stub."""
    raise RuntimeError("This project uses RAGAS. Call evaluate_with_ragas() instead.")


def evaluate_with_trulens(*_args, **_kwargs):
    """The project selected RAGAS; retained only as an explicit compatibility stub."""
    raise RuntimeError("This project uses RAGAS. Call evaluate_with_ragas() instead.")


DEFAULT_CONFIGS = {
    "hybrid_rerank": {
        "retrieval_mode": "hybrid", "use_reranking": True, "use_fallback": True,
    },
    "dense_only": {
        "retrieval_mode": "dense", "use_reranking": False, "use_fallback": False,
    },
}


def compare_configs(
    rag_pipeline: Any,
    golden_dataset: list[dict],
    configs: Mapping[str, Mapping[str, Any]] | None = None,
) -> dict[str, dict]:
    """Evaluate at least two retrieval configurations with the same dataset.

    ``rag_pipeline`` may also be a mapping from configuration name to two
    separately configured pipeline callables. This is useful when configuration
    is performed at construction time rather than through function arguments.
    """
    configs = dict(configs or DEFAULT_CONFIGS)
    if len(configs) < 2:
        raise ValueError("A/B comparison requires at least two configurations")

    results: dict[str, dict] = {}
    for name, params in configs.items():
        print(f"\n=== Evaluating {name} ===")
        if isinstance(rag_pipeline, Mapping):
            if name not in rag_pipeline:
                raise KeyError(f"Missing pipeline for configuration '{name}'")
            pipeline, effective_params = rag_pipeline[name], None
        else:
            pipeline, effective_params = rag_pipeline, params
        results[name] = evaluate_with_ragas(
            pipeline, golden_dataset, config=effective_params, config_name=name
        )
    return results


def _format_score(value: float | None) -> str:
    return "N/A" if value is None else f"{value:.3f}"


def _worst_rows(result: dict, limit: int = 3) -> list[dict]:
    rows = result.get("rows", [])
    def row_average(row: dict) -> float:
        values = [row.get(metric) for metric in METRICS if row.get(metric) is not None]
        return mean(values) if values else float("inf")
    return sorted(rows, key=row_average)[:limit]


def export_results(results: dict | None, comparison: dict[str, dict]) -> Path:
    """Write a reproducible Markdown report to ``results.md``."""
    if not comparison:
        if results is None:
            raise ValueError("No evaluation results to export")
        comparison = {results.get("config", "default"): results}

    names = list(comparison)
    first, second = names[0], names[1] if len(names) > 1 else None
    lines = [
        "# RAG Evaluation Results", "", "## Framework", "",
        "RAGAS 0.1.21 với 20 câu hỏi trong `golden_dataset.json`.", "",
        "## Overall Scores", "",
        f"| Metric | {first} | {second or '-'} | Δ |",
        "|---|---:|---:|---:|",
    ]
    for metric in (*METRICS, "average"):
        left = comparison[first]["overall"].get(metric)
        right = comparison[second]["overall"].get(metric) if second else None
        delta = left - right if left is not None and right is not None else None
        label = "Average" if metric == "average" else METRIC_LABELS[metric]
        lines.append(
            f"| {label} | {_format_score(left)} | {_format_score(right)} | "
            f"{_format_score(delta)} |"
        )

    lines += ["", "## A/B Comparison", ""]
    if second:
        left_average = comparison[first]["overall"].get("average")
        right_average = comparison[second]["overall"].get("average")
        if left_average is not None and right_average is not None:
            winner = first if left_average >= right_average else second
            lines.append(f"Cấu hình **{winner}** có điểm trung bình cao hơn trên bộ kiểm thử.")
        else:
            lines.append("Không đủ điểm hợp lệ để kết luận cấu hình tốt hơn.")
    else:
        lines.append("Chưa có cấu hình thứ hai để so sánh A/B.")

    lines += ["", "## Worst Performers (Bottom 3)", "",
              "| # | Question | Faithfulness | Relevance | Recall | Precision |",
              "|---:|---|---:|---:|---:|---:|"]
    for index, row in enumerate(_worst_rows(comparison[first]), 1):
        question = row["question"].replace("|", "\\|")
        lines.append(
            f"| {index} | {question} | {_format_score(row['faithfulness'])} | "
            f"{_format_score(row['answer_relevancy'])} | "
            f"{_format_score(row['context_recall'])} | "
            f"{_format_score(row['context_precision'])} |"
        )

    lines += [
        "", "## Recommendations", "",
        "1. Kiểm tra các câu có Context Recall thấp và bổ sung query expansion hoặc điều chỉnh `top_k`.",
        "2. Với Context Precision thấp, hiệu chỉnh BM25/RRF và reranker để loại chunk nhiễu.",
        "3. Với Faithfulness thấp, siết system prompt và yêu cầu từ chối khi context không đủ bằng chứng.",
        "", "## Reproduction", "", "```powershell",
        ".\\.venv\\Scripts\\python.exe -m group_project.evaluation.eval_pipeline",
        "```", "",
    ]
    RESULTS_PATH.write_text("\n".join(lines), encoding="utf-8")
    return RESULTS_PATH


def main(limit: int | None = None) -> int:
    golden_dataset = load_golden_dataset()
    if limit is not None:
        if limit <= 0:
            raise ValueError("--limit must be greater than zero")
        golden_dataset = golden_dataset[:limit]
    print(f"Loaded {len(golden_dataset)} test cases")

    from src.task10_generation import generate_with_citation

    comparison = compare_configs(generate_with_citation, golden_dataset)
    report_path = export_results(None, comparison)
    print(f"Report written to {report_path}")
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Evaluate the RAG pipeline with RAGAS")
    parser.add_argument("--limit", type=int, help="Evaluate only the first N cases")
    arguments = parser.parse_args()
    try:
        exit_code = main(arguments.limit)
    except (ImportError, RuntimeError, TypeError, ValueError) as exc:
        parser.exit(1, f"Evaluation cannot start: {exc}\n")
    raise SystemExit(exit_code)
