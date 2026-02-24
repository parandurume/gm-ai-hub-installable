"""실사용 문서에서 MIPROv2 학습 예시 자동 추출."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import dspy


async def build_dataset(
    pipeline_name: str,
    min_examples: int = 10,
    val_ratio: float = 0.2,
) -> tuple[list[dspy.Example], list[dspy.Example]]:
    """학습/검증 데이터셋 반환."""
    examples: list[dict] = []

    # 1a. 디렉토리 기반 예시 로드 (data/examples/{pipeline}/*.json)
    example_dir = Path(f"data/examples/{pipeline_name}")
    if example_dir.exists() and example_dir.is_dir():
        for fp in example_dir.glob("*.json"):
            try:
                data = json.loads(fp.read_text(encoding="utf-8"))
                if isinstance(data, list):
                    examples.extend(data)
                elif isinstance(data, dict):
                    examples.append(data)
            except Exception:
                pass

    # 1b. 플랫 파일 로드 (data/examples/{pipeline}_examples.json)
    flat_file = Path(f"data/examples/{pipeline_name}_examples.json")
    if flat_file.exists():
        try:
            data = json.loads(flat_file.read_text(encoding="utf-8"))
            if isinstance(data, list):
                examples.extend(data)
            elif isinstance(data, dict):
                examples.append(data)
        except Exception:
            pass

    print(f"   수작업 예시: {len(examples)}개")

    # 2. 예시 부족 시 합성 생성
    if len(examples) < min_examples:
        print(f"   예시 부족 ({len(examples)}/{min_examples}), 자동 생성으로 보완")
        auto = _generate_synthetic_examples(
            pipeline_name, min_examples - len(examples)
        )
        examples.extend(auto)

    # DSPy Example 변환
    dspy_examples = []
    for e in examples:
        try:
            ex = dspy.Example(**e)
            if pipeline_name == "gianmun":
                ex = ex.with_inputs("user_request", "doc_type", "current_year")
            elif pipeline_name == "docent":
                ex = ex.with_inputs(
                    "user_request", "target_count", "duration_months", "current_year"
                )
            elif pipeline_name == "complaint":
                ex = ex.with_inputs("complaint_text", "current_year")
            elif pipeline_name == "meeting":
                ex = ex.with_inputs("raw_content", "attendees", "current_year")
            dspy_examples.append(ex)
        except Exception:
            pass

    # 분할
    split = int(len(dspy_examples) * (1 - val_ratio))
    return dspy_examples[:split], dspy_examples[split:]


def _generate_synthetic_examples(pipeline_name: str, count: int) -> list[dict]:
    """합성 예시 생성."""
    year = date.today().year
    templates: dict[str, dict] = {
        "gianmun": {
            "user_request": "AI 도슨트 육성사업 협조 요청",
            "doc_type": "협조전",
            "current_year": year,
            "body": (
                f"{year}년 AI 도슨트 육성사업 추진과 관련하여 "
                "귀 기관의 협조를 요청드립니다.\n\n"
                "1. 추진 배경\n   ...(작성)...\n\n"
                "2. 협조 요청 사항\n   ...(작성)..."
            ),
            "fiscal_year": year,
        },
        "docent": {
            "user_request": "AI 도슨트 육성사업 1기 계획서",
            "target_count": 30,
            "duration_months": 9,
            "current_year": year,
            "fiscal_year": year,
            "total_krw": 50_000_000,
            "items": [
                {"category": "강사비", "unit": "시간", "quantity": 100,
                 "unit_price": 100_000, "total_krw": 10_000_000},
                {"category": "운영비", "unit": "식", "quantity": 9,
                 "unit_price": 2_000_000, "total_krw": 18_000_000},
                {"category": "교육비", "unit": "명", "quantity": 30,
                 "unit_price": 200_000, "total_krw": 6_000_000},
                {"category": "인건비", "unit": "월", "quantity": 9,
                 "unit_price": 1_777_778, "total_krw": 16_000_000},
            ],
        },
        "complaint": {
            "complaint_text": "AI 도슨트 교육 신청 방법을 알고 싶습니다.",
            "current_year": year,
            "classification": "단순질의",
            "response_body": (
                "귀하의 민원에 대하여 다음과 같이 답변드립니다.\n\n"
                f"AI 도슨트 교육 신청은 {year}년 중 광명시 공식 홈페이지에서 가능합니다."
            ),
        },
        "meeting": {
            "raw_content": "1분기 실적 보고 및 2분기 계획 논의",
            "attendees": "김과장, 이대리, 박주무관",
            "current_year": year,
            "summary": (
                "1. 1분기 AI 도슨트 사업 추진 현황 보고\n"
                "2. 2분기 교육 과정 확정 논의\n"
                "결정: 예산 품의 3월 말까지 완료"
            ),
        },
    }
    template = templates.get(pipeline_name, {})
    return [template.copy() for _ in range(count)]
