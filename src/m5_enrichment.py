from __future__ import annotations

"""
Module 5: Enrichment Pipeline
==============================
Làm giàu chunks TRƯỚC khi embed: Summarize, HyQA, Contextual Prepend, Auto Metadata.

Test: pytest tests/test_m5.py
"""

import os, sys, re, json, hashlib
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")
from dataclasses import dataclass, field

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import OPENAI_API_KEY


@dataclass
class EnrichedChunk:
    """Chunk đã được làm giàu."""
    original_text: str
    enriched_text: str
    summary: str
    hypothesis_questions: list[str]
    auto_metadata: dict
    method: str  # "contextual", "summary", "hyqa", "full"


# ─── OpenAI helper ───────────────────────────────────────

ENRICH_MODEL = "gpt-4o-mini"
_client = None


def _chat(system: str, user: str, max_tokens: int, json_mode: bool = False) -> str | None:
    """Gọi gpt-4o-mini. Trả về None nếu không có key hoặc API lỗi (caller tự fallback)."""
    global _client
    if not OPENAI_API_KEY:
        return None
    try:
        if _client is None:
            from openai import OpenAI
            _client = OpenAI(timeout=60, max_retries=2)
        kwargs = {"response_format": {"type": "json_object"}} if json_mode else {}
        resp = _client.chat.completions.create(
            model=ENRICH_MODEL,
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
            max_tokens=max_tokens,
            temperature=0,
            **kwargs,
        )
        return (resp.choices[0].message.content or "").strip() or None
    except Exception as e:
        print(f"  ⚠️  OpenAI call failed: {e}")
        return None


def _parse_json(raw: str | None) -> dict:
    """Parse JSON an toàn (bỏ ```json fence nếu có). Lỗi → {}."""
    if not raw:
        return {}
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.strip("`").removeprefix("json").strip()
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        print(f"  ⚠️  JSON parse failed: {e}")
        return {}
    return data if isinstance(data, dict) else {}


# ─── Technique 1: Chunk Summarization ────────────────────


def summarize_chunk(text: str) -> str:
    """
    Tạo summary ngắn cho chunk.
    Embed summary thay vì (hoặc cùng với) raw chunk → giảm noise.
    """
    summary = _chat("Tóm tắt đoạn văn sau trong 2-3 câu ngắn gọn bằng tiếng Việt. "
                    "Giữ nguyên mọi con số, mốc thời gian và điều kiện.", text, max_tokens=150)
    if summary:
        return summary

    # Extractive fallback (không cần API): 2 câu đầu.
    sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', text.replace("\n", " ")) if s.strip()]
    return " ".join(sentences[:2]) if sentences else text


# ─── Technique 2: Hypothesis Question-Answer (HyQA) ─────


def generate_hypothesis_questions(text: str, n_questions: int = 3) -> list[str]:
    """
    Generate câu hỏi mà chunk có thể trả lời.
    Index cả questions lẫn chunk → query match tốt hơn (bridge vocabulary gap).
    """
    raw = _chat(f"Dựa trên đoạn văn, tạo {n_questions} câu hỏi bằng tiếng Việt mà đoạn văn có thể "
                "trả lời. Trả về mỗi câu hỏi trên 1 dòng, không đánh số.", text, max_tokens=200)
    if raw:
        questions = [q.strip().lstrip("0123456789.-)• ").strip() for q in raw.split("\n")]
        questions = [q for q in questions if q]
        if questions:
            return questions[:n_questions]

    # Extractive fallback: biến câu khẳng định thành câu hỏi.
    sentences = [s.strip() for s in re.split(r'[.!?\n]', text) if len(s.strip()) > 10]
    return [f"{s.rstrip('.')}?" for s in sentences[:n_questions]]


# ─── Technique 3: Contextual Prepend (Anthropic style) ──


def contextual_prepend(text: str, document_title: str = "") -> str:
    """
    Prepend context giải thích chunk nằm ở đâu trong document.
    Anthropic benchmark: giảm 49% retrieval failure (alone).
    """
    context = _chat("Viết 1 câu ngắn bằng tiếng Việt mô tả đoạn văn này nằm ở đâu trong tài liệu "
                    "và nói về chủ đề gì. Chỉ trả về 1 câu.",
                    f"Tài liệu: {document_title}\n\nĐoạn văn:\n{text}", max_tokens=80)
    if context:
        return f"{context}\n\n{text}"

    # Simple fallback: ghép tên tài liệu. Luôn giữ nguyên văn text gốc.
    prefix = f"Trích từ {document_title}. " if document_title else ""
    return f"{prefix}{text}"


# ─── Technique 4: Auto Metadata Extraction ──────────────

_DEFAULT_METADATA = {"topic": "general", "entities": [], "category": "policy", "language": "vi"}


def extract_metadata(text: str) -> dict:
    """
    LLM extract metadata tự động: topic, entities, date_range, category.
    """
    data = _parse_json(_chat(
        'Trích xuất metadata từ đoạn văn. Trả về JSON: {"topic": "...", "entities": ["..."], '
        '"category": "policy|hr|it|finance", "language": "vi|en"}',
        text, max_tokens=150, json_mode=True))
    return {**_DEFAULT_METADATA, **data} if data else dict(_DEFAULT_METADATA)


# ─── Combined Single-Call Mode ───────────────────────────

_COMBINED_PROMPT = """Bạn làm giàu (enrich) một đoạn trích từ tài liệu chính sách nội bộ công ty để phục vụ tìm kiếm.
Phân tích đoạn văn và trả về JSON đúng schema:
{
  "summary": "tóm tắt 2-3 câu, giữ nguyên mọi con số và điều kiện",
  "questions": ["câu hỏi 1", "câu hỏi 2", "câu hỏi 3"],
  "context": "1 câu cho biết đoạn văn thuộc tài liệu/chính sách nào, mục nào, nói về gì; nêu phiên bản và trạng thái (hiện hành / đã bị thay thế) nếu có",
  "metadata": {"topic": "...", "entities": ["..."], "category": "policy|hr|it|finance", "language": "vi|en"}
}
Chỉ dùng thông tin có trong tài liệu, không suy diễn. Viết bằng tiếng Việt."""


def _enrich_single_call(text: str, source: str) -> dict:
    """Single LLM call to get summary + questions + context + metadata.

    ⚠️ Cost optimization: 1 API call thay vì 4 calls riêng lẻ.
    """
    user = f"Tài liệu: {source}\n\nĐoạn văn:\n{text}"
    key = hashlib.sha256(f"{ENRICH_MODEL}\n{_COMBINED_PROMPT}\n{user}".encode("utf-8")).hexdigest()
    cache = _load_cache()
    if key in cache:
        return cache[key]

    data = _parse_json(_chat(_COMBINED_PROMPT, user, max_tokens=500, json_mode=True))
    if not data:
        return {}

    # Chuẩn hóa kiểu dữ liệu để enrich_chunks() dùng an toàn.
    questions = data.get("questions", [])
    metadata = data.get("metadata", {})
    result = {
        "summary": str(data.get("summary", "")).strip(),
        "questions": [str(q).strip() for q in questions if str(q).strip()] if isinstance(questions, list) else [],
        "context": str(data.get("context", "")).strip(),
        "metadata": metadata if isinstance(metadata, dict) else {},
    }
    cache[key] = result
    _save_cache(cache)
    return result


# Cache kết quả enrichment trên đĩa (key = hash của model + prompt + chunk): chạy lại pipeline
# không phải trả lại 1 call/chunk. Chỉ cache kết quả thành công; lỗi/fallback không được cache.
_CACHE_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                           ".cache", "enrichment_cache.json")
_cache: dict | None = None


def _load_cache() -> dict:
    global _cache
    if _cache is None:
        try:
            with open(_CACHE_PATH, encoding="utf-8") as f:
                _cache = json.load(f)
        except (OSError, json.JSONDecodeError):
            _cache = {}
    return _cache


def _save_cache(cache: dict) -> None:
    try:
        os.makedirs(os.path.dirname(_CACHE_PATH), exist_ok=True)
        with open(_CACHE_PATH, "w", encoding="utf-8") as f:
            json.dump(cache, f, ensure_ascii=False)
    except OSError as e:
        print(f"  ⚠️  Không ghi được enrichment cache: {e}")


# ─── Full Enrichment Pipeline ────────────────────────────


def enrich_chunks(
    chunks: list[dict],
    methods: list[str] | None = None,
) -> list[EnrichedChunk]:
    """
    Chạy enrichment pipeline trên danh sách chunks. (Đã implement sẵn — dùng functions ở trên)

    Có 2 chế độ:
    - methods cụ thể (["summary"], ["contextual"]...): gọi từng function riêng (tốt cho học/debug)
    - methods=["combined"] hoặc None: 1 API call duy nhất cho tất cả (tốt cho production)

    Args:
        chunks: List of {"text": str, "metadata": dict}
        methods: Default None → combined mode (1 call/chunk).
                 Options: "summary", "hyqa", "contextual", "metadata", "combined"
    """
    if methods is None:
        methods = ["combined"]

    use_combined = "combined" in methods

    enriched = []
    for i, chunk in enumerate(chunks):
        text = chunk["text"]
        source = chunk.get("metadata", {}).get("source", "")

        if use_combined:
            result = _enrich_single_call(text, source)
            summary = result.get("summary", "")
            questions = result.get("questions", [])
            context_line = result.get("context", "")
            enriched_text = f"{context_line}\n\n{text}" if context_line else text
            auto_meta = result.get("metadata", {})
        else:
            summary = summarize_chunk(text) if "summary" in methods else ""
            questions = generate_hypothesis_questions(text) if "hyqa" in methods else []
            enriched_text = contextual_prepend(text, source) if "contextual" in methods else text
            auto_meta = extract_metadata(text) if "metadata" in methods else {}

        enriched.append(EnrichedChunk(
            original_text=text,
            enriched_text=enriched_text,
            summary=summary,
            hypothesis_questions=questions,
            auto_metadata={**chunk.get("metadata", {}), **auto_meta},
            method="+".join(methods),
        ))

        if (i + 1) % 10 == 0 or (i + 1) == len(chunks):
            print(f"  Enriched {i + 1}/{len(chunks)} chunks...", flush=True)

    return enriched


# ─── Main ────────────────────────────────────────────────

if __name__ == "__main__":
    sample = "Nhân viên chính thức được nghỉ phép năm 12 ngày làm việc mỗi năm. Số ngày nghỉ phép tăng thêm 1 ngày cho mỗi 5 năm thâm niên công tác."

    print("=== Enrichment Pipeline Demo ===\n")
    print(f"Original: {sample}\n")

    s = summarize_chunk(sample)
    print(f"Summary: {s}\n")

    qs = generate_hypothesis_questions(sample)
    print(f"HyQA questions: {qs}\n")

    ctx = contextual_prepend(sample, "Sổ tay nhân viên VinUni 2024")
    print(f"Contextual: {ctx}\n")

    meta = extract_metadata(sample)
    print(f"Auto metadata: {meta}")
