from __future__ import annotations

"""Module 4: RAGAS Evaluation — 4 metrics + failure analysis."""

import os, sys, json, math, re
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")
from dataclasses import dataclass

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import TEST_SET_PATH


@dataclass
class EvalResult:
    question: str
    answer: str
    contexts: list[str]
    ground_truth: str
    faithfulness: float
    answer_relevancy: float
    context_precision: float
    context_recall: float


METRICS = ["faithfulness", "answer_relevancy", "context_precision", "context_recall"]


def _safe_float(value) -> float:
    """NaN / None / giá trị lạ → 0.0."""
    try:
        f = float(value)
    except (TypeError, ValueError):
        return 0.0
    return 0.0 if math.isnan(f) else f


def _nan_mean(values: list) -> float:
    valid = []
    for v in values:
        try:
            f = float(v)
        except (TypeError, ValueError):
            continue
        if not math.isnan(f):
            valid.append(f)
    return sum(valid) / len(valid) if valid else 0.0


def load_test_set(path: str = TEST_SET_PATH) -> list[dict]:
    """Load test set from JSON. (Đã implement sẵn)"""
    with open(path, encoding="utf-8") as f:
        return json.load(f)


EVAL_LLM_MODEL = "gpt-4o-mini"
EVAL_EMBEDDING_MODEL = "text-embedding-3-small"
NAN_RETRIES = 2  # RAGAS trả NaN khi một lời gọi LLM lỗi/parse hỏng → chấm lại đúng các câu đó.


def _is_valid_score(value) -> bool:
    try:
        f = float(value)
    except (TypeError, ValueError):
        return False
    return math.isfinite(f) and 0.0 <= f <= 1.0


class _LineSentenceSegmenter:
    """Segmenter cho faithfulness của ragas 0.1.x.

    Faithfulness chỉ giữ các câu kết thúc bằng "." trước khi tách statement; answer dạng
    markdown/gạch đầu dòng ("- Thử việc tiêu chuẩn: **60 ngày**") bị bỏ hết câu → không có
    statement → NaN tất định. Tách theo dòng, bỏ ký hiệu markdown và thêm "." cho câu thiếu dấu
    kết câu; bỏ dòng dẫn kết thúc bằng ":" ("Dựa trên context:") vì nội dung nằm ở các dòng sau.
    Answer gốc vẫn được truyền nguyên văn vào prompt; chỉ danh sách câu thay đổi.
    """

    def __init__(self, base):
        self.base = base

    def segment(self, text: str) -> list[str]:
        sentences = []
        for line in text.splitlines():
            line = re.sub(r"^\s*(?:[-*+]|\d+[.)])\s+", "", line).replace("**", "").strip()
            for sentence in self.base.segment(line) if line else []:
                sentence = sentence.strip()
                if sentence and not sentence.endswith(":"):
                    sentences.append(sentence if sentence.endswith(".") else sentence + ".")
        return sentences


def _faithfulness_metric():
    from ragas.metrics import Faithfulness
    from ragas.metrics.base import get_segmenter

    metric = Faithfulness()
    metric.sentence_segmenter = _LineSentenceSegmenter(get_segmenter(language="english", clean=False))
    return metric


def _run_ragas(questions, answers, contexts, ground_truths, llm, embeddings) -> list[dict]:
    """Một lượt RAGAS; trả list dict 4 metric theo đúng thứ tự đầu vào (có thể còn NaN)."""
    from ragas import evaluate
    from ragas.metrics import answer_relevancy, context_precision, context_recall
    from datasets import Dataset

    faithfulness = _faithfulness_metric()

    dataset = Dataset.from_dict({
        "question": list(questions), "answer": list(answers),
        "contexts": [list(c) for c in contexts], "ground_truth": list(ground_truths),
    })
    result = evaluate(
        dataset,
        metrics=[faithfulness, answer_relevancy, context_precision, context_recall],
        llm=llm, embeddings=embeddings, raise_exceptions=False,
    )
    df = result.to_pandas()
    if len(df) != len(questions):
        raise ValueError(f"RAGAS trả {len(df)} rows cho {len(questions)} câu hỏi.")
    return [{m: row.get(m) for m in METRICS} for _, row in df.iterrows()]


def evaluate_ragas(questions: list[str], answers: list[str],
                   contexts: list[list[str]], ground_truths: list[str]) -> dict:
    """Run RAGAS evaluation.

    Day 24 adapter: không nuốt lỗi và không đổi NaN thành 0.0 (điểm giả). Câu nào còn
    NaN được chấm lại tối đa NAN_RETRIES lượt; nếu vẫn NaN thì raise để người chạy xử lý.
    metadata.evaluator_models ghi model IDs thực sự truyền vào RAGAS trong lượt này.
    """
    n = len(questions)
    if not (len(answers) == len(contexts) == len(ground_truths) == n):
        raise ValueError("questions/answers/contexts/ground_truths phải cùng độ dài.")

    from langchain_openai import ChatOpenAI, OpenAIEmbeddings

    # Chỉ định model rõ ràng: default của ragas 0.1 (gpt-3.5-turbo-16k, ada-002) đã cũ.
    llm = ChatOpenAI(model=EVAL_LLM_MODEL, temperature=0)
    embeddings = OpenAIEmbeddings(model=EVAL_EMBEDDING_MODEL)
    evaluator_models = [llm.model_name, embeddings.model]

    scores = _run_ragas(questions, answers, contexts, ground_truths, llm, embeddings)
    for attempt in range(1, NAN_RETRIES + 1):
        pending = [i for i, row in enumerate(scores)
                   if not all(_is_valid_score(row[m]) for m in METRICS)]
        if not pending:
            break
        print(f"  ↻ RAGAS retry {attempt}/{NAN_RETRIES}: {len(pending)} câu còn NaN")
        rescored = _run_ragas([questions[i] for i in pending], [answers[i] for i in pending],
                              [contexts[i] for i in pending], [ground_truths[i] for i in pending],
                              llm, embeddings)
        for i, row in zip(pending, rescored):
            # Chỉ thay metric còn lỗi, giữ metric đã chấm hợp lệ ở lượt trước.
            for m in METRICS:
                if not _is_valid_score(scores[i][m]) and _is_valid_score(row[m]):
                    scores[i][m] = row[m]

    invalid = [(i, m) for i, row in enumerate(scores) for m in METRICS
               if not _is_valid_score(row[m])]
    if invalid:
        raise ValueError(f"RAGAS vẫn trả NaN/không hợp lệ sau {NAN_RETRIES} lượt chấm lại: {invalid}")

    per_question = [EvalResult(
        question=questions[i], answer=answers[i], contexts=list(contexts[i]),
        ground_truth=ground_truths[i], **{m: float(scores[i][m]) for m in METRICS},
    ) for i in range(n)]
    aggregate = {m: sum(getattr(r, m) for r in per_question) / n for m in METRICS}
    return {**aggregate, "per_question": per_question,
            "metadata": {"evaluator_models": evaluator_models}}



def failure_analysis(eval_results: list[EvalResult], bottom_n: int = 10) -> list[dict]:
    """Analyze bottom-N worst questions using Diagnostic Tree."""
    diagnostic_tree = {
        "faithfulness": ("LLM hallucinating", "Tighten prompt, lower temperature"),
        "context_recall": ("Missing relevant chunks", "Improve chunking or add BM25"),
        "context_precision": ("Too many irrelevant chunks", "Add reranking or metadata filter"),
        "answer_relevancy": ("Answer doesn't match question", "Improve prompt template"),
    }

    analyzed = []
    for r in eval_results:
        scores = {m: _safe_float(getattr(r, m)) for m in METRICS}
        avg = sum(scores.values()) / len(scores)
        worst_metric = min(scores, key=scores.get)
        diagnosis, suggested_fix = diagnostic_tree[worst_metric]
        analyzed.append({
            "question": r.question,
            "worst_metric": worst_metric,
            "score": round(avg, 4),
            "worst_score": round(scores[worst_metric], 4),
            "diagnosis": diagnosis,
            "suggested_fix": suggested_fix,
            "metrics": {m: round(s, 4) for m, s in scores.items()},
            "answer": r.answer,
            "ground_truth": r.ground_truth,
            "contexts": r.contexts,
        })

    analyzed.sort(key=lambda x: x["score"])
    return analyzed[:bottom_n]


def save_report(results: dict, failures: list[dict], path: str = "reports/ragas_report.json"):
    """Save evaluation report to JSON. (Đã implement sẵn)"""
    parent_dir = os.path.dirname(path)
    if parent_dir:
        os.makedirs(parent_dir, exist_ok=True)
    report = {
        "aggregate": {k: v for k, v in results.items() if k != "per_question"},
        "num_questions": len(results.get("per_question", [])),
        "failures": failures,
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"Report saved to {path}")


if __name__ == "__main__":
    test_set = load_test_set()
    print(f"Loaded {len(test_set)} test questions")
    print("Run pipeline.py first to generate answers, then call evaluate_ragas().")
