"""공문서 생성 관련 DSPy Signature."""

from __future__ import annotations

import dspy


class ClassifyDocument(dspy.Signature):
    """문서를 유형별로 분류한다."""

    user_request: str = dspy.InputField(desc="사용자 요청")
    current_year: int = dspy.InputField(desc="현재 연도")
    doc_type: str = dspy.OutputField(
        desc="문서 유형: 일반기안, 협조전, 보고서, 계획서, 결과보고서, 회의록, 민원답변"
    )
    confidence: float = dspy.OutputField(desc="분류 신뢰도 (0~1)")


class GenerateDraftBody(dspy.Signature):
    """공문서 초안(Draft) 본문을 생성한다."""

    user_request: str = dspy.InputField(desc="사용자 지시")
    doc_type: str = dspy.InputField(desc="문서 종류")
    current_year: int = dspy.InputField(desc="현재 연도")
    recipients: str = dspy.InputField(desc="수신처", default="")
    body: str = dspy.OutputField(desc="공문서 본문 (한국어, 경어체)")
    fiscal_year: int = dspy.OutputField(desc="회계연도")


class SummarizeDocument(dspy.Signature):
    """문서 내용을 요약한다."""

    content: str = dspy.InputField(desc="원본 문서 텍스트")
    current_year: int = dspy.InputField(desc="현재 연도")
    summary: str = dspy.OutputField(desc="3~5문장 요약")
    key_points: list[str] = dspy.OutputField(desc="핵심 요점 목록")


class DraftComplaintResponse(dspy.Signature):
    """민원 답변 초안을 작성한다."""

    complaint_text: str = dspy.InputField(desc="민원 내용")
    current_year: int = dspy.InputField(desc="현재 연도")
    classification: str = dspy.OutputField(
        desc="민원 유형: 단순질의, 민원처리, 이의신청, 건의"
    )
    response_body: str = dspy.OutputField(desc="공식 답변 본문 (경어체)")
    legal_refs: list[str] = dspy.OutputField(desc="관련 법령/규정")


class SummarizeMeeting(dspy.Signature):
    """회의 내용을 회의록으로 정리한다."""

    raw_content: str = dspy.InputField(desc="회의 내용 (원문/메모)")
    attendees: str = dspy.InputField(desc="참석자 목록")
    current_year: int = dspy.InputField(desc="현재 연도")
    summary: str = dspy.OutputField(desc="회의 요약")
    decisions: list[str] = dspy.OutputField(desc="결정사항")
    action_items: list[str] = dspy.OutputField(desc="후속조치")
