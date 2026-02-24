"""AI 도슨트 육성사업 계획서 생성 Signature."""

from __future__ import annotations

import dspy


class ClassifyDocentProject(dspy.Signature):
    """AI 도슨트 프로젝트를 분류한다."""

    user_request: str = dspy.InputField(desc="사용자 요청")
    current_year: int = dspy.InputField(desc="현재 연도")
    reference_projects: str = dspy.InputField(desc="참고 사업 사례", default="")
    project_type: str = dspy.OutputField(
        desc="사업 유형: 신규, 계속, 확대, 시범"
    )
    target_audience: str = dspy.OutputField(desc="대상 (예: 시민, 공무원)")
    scope: str = dspy.OutputField(desc="사업 범위 설명")


class ReasonDocentBudget(dspy.Signature):
    """AI 도슨트 사업 예산을 산출한다."""

    project_title: str = dspy.InputField(desc="사업명")
    target_count: int = dspy.InputField(desc="대상 인원")
    duration_months: int = dspy.InputField(desc="사업 기간(월)")
    current_year: int = dspy.InputField(desc="현재 연도")
    budget_guidelines: str = dspy.InputField(desc="예산 편성 지침", default="")
    fiscal_year: int = dspy.OutputField(desc="회계연도")
    total_krw: int = dspy.OutputField(desc="총예산(원)")
    items: list[dict] = dspy.OutputField(
        desc="예산 항목 [{category, unit, quantity, unit_price, total_krw}]"
    )
    rationale: str = dspy.OutputField(desc="예산 산출 근거 설명")


class GenerateDocentBackground(dspy.Signature):
    """AI 도슨트 사업 추진배경을 생성한다."""

    project_title: str = dspy.InputField(desc="사업명")
    current_year: int = dspy.InputField(desc="현재 연도")
    gwangmyeong_context: str = dspy.InputField(desc="광명시 관련 맥락", default="")
    ai_trend_context: str = dspy.InputField(desc="AI 트렌드 맥락", default="")
    background_paragraphs: list[str] = dspy.OutputField(
        desc="추진배경 문단 목록 (3~5개)"
    )


class GenerateDocentImplementation(dspy.Signature):
    """AI 도슨트 사업 추진계획을 생성한다."""

    project_title: str = dspy.InputField(desc="사업명")
    target_count: int = dspy.InputField(desc="대상 인원")
    budget_total: int = dspy.InputField(desc="총예산")
    background: list[str] = dspy.InputField(desc="추진배경")
    current_year: int = dspy.InputField(desc="현재 연도")
    phases: list[dict] = dspy.OutputField(
        desc="추진단계 [{name, start_month, end_month, description}]"
    )
    expected_outcomes: list[str] = dspy.OutputField(desc="기대효과 목록")
    implementation_body: str = dspy.OutputField(desc="추진내용 본문")
