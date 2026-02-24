"""
MIPROv2 평가 메트릭 (RULE-15: 모두 정규식/수식 기반, 외부 LLM 금지).

각 메트릭: (example, prediction, trace) → float (0.0 ~ 1.0)
"""

from __future__ import annotations

from datetime import date

from backend.ai.guards import DateGuard


def date_accuracy_metric(example, prediction, trace=None) -> float:
    """구식 연도 없으면 1.0, 있으면 0.0."""
    year = date.today().year

    fiscal = getattr(prediction, "fiscal_year", None)
    if fiscal is not None:
        try:
            if int(fiscal) < year:
                return 0.0
        except (ValueError, TypeError):
            return 0.5

    texts = []
    for attr in ["body", "content", "background", "implementation",
                 "background_paragraphs", "response_body"]:
        val = getattr(prediction, attr, None)
        if isinstance(val, str):
            texts.append(val)
        elif isinstance(val, list):
            texts.extend(str(v) for v in val)

    if not texts:
        return 1.0

    scan = DateGuard.scan(" ".join(texts))
    return 1.0 if scan["passed"] else 0.0


def budget_consistency_metric(example, prediction, trace=None) -> float:
    """항목 합계 = 총액 +/- 1% 이내이면 1.0."""
    total = getattr(prediction, "total_krw", None)
    items = getattr(prediction, "items", None)

    if total is None or items is None:
        return 1.0

    try:
        total_int = int(str(total).replace(",", "").replace("원", "").strip())
        item_total = sum(
            int(str(i.get("total_krw", 0)).replace(",", "")) for i in items
        )
        if total_int == 0:
            return 0.0
        ratio = abs(item_total - total_int) / total_int
        return 1.0 if ratio <= 0.01 else max(0.0, 1.0 - ratio * 10)
    except Exception:
        return 0.5


def document_structure_metric(example, prediction, trace=None) -> float:
    """필수 섹션 존재 여부."""
    required_sections = getattr(
        example, "required_sections", ["추진배경", "추진내용", "기대효과"]
    )
    content = ""
    for attr in ["body", "content", "background_paragraphs",
                 "implementation_body", "response_body"]:
        val = getattr(prediction, attr, None)
        if isinstance(val, str):
            content += val
        elif isinstance(val, list):
            content += " ".join(str(v) for v in val)

    if not content:
        return 0.0

    found = sum(1 for s in required_sections if s in content)
    return found / len(required_sections)


def korean_formality_metric(example, prediction, trace=None) -> float:
    """공문서 경어·격식 표현 사용 (규칙 기반)."""
    formal_endings = ["습니다", "입니다", "합니다", "됩니다", "바랍니다", "드립니다"]
    informal_endings = ["해요", "이에요", "어요", "죠", "군요"]

    content = ""
    for attr in ["body", "content", "response_body", "summary"]:
        val = getattr(prediction, attr, "")
        if isinstance(val, str):
            content += val

    if not content:
        return 0.5

    formal_count = sum(content.count(e) for e in formal_endings)
    informal_count = sum(content.count(e) for e in informal_endings)
    total = formal_count + informal_count

    if total == 0:
        return 0.5
    return formal_count / total


def combined_metric(example, prediction, trace=None) -> float:
    """복합 메트릭 (가중 평균). 날짜 0.35 + 예산 0.30 + 구조 0.20 + 경어 0.15."""
    scores = {
        "date": (date_accuracy_metric(example, prediction, trace), 0.35),
        "budget": (budget_consistency_metric(example, prediction, trace), 0.30),
        "structure": (document_structure_metric(example, prediction, trace), 0.20),
        "formality": (korean_formality_metric(example, prediction, trace), 0.15),
    }
    return sum(s * w for s, w in scores.values())
