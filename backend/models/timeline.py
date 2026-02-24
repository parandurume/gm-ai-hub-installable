"""사업 일정 관련 Pydantic 모델 (RULE-03)."""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, Field, field_validator


class Phase(BaseModel):
    """사업 추진 단계."""

    name: str = Field(..., description="단계명 (예: 1단계 기본교육)")
    start_month: str = Field(..., description="시작 (예: 3월)")
    end_month: str = Field(..., description="종료 (예: 5월)")
    description: str = Field("", description="단계 설명")


class DocumentTimeline(BaseModel):
    """사업 추진 일정 (AI 출력 검증용)."""

    year: int = Field(..., description="사업 연도")
    title: str = Field(..., description="사업명")
    phases: list[Phase] = Field(..., min_length=1, description="추진 단계")
    total_months: int = Field(..., ge=1, le=36, description="총 사업 기간(월)")

    @field_validator("year")
    @classmethod
    def year_not_stale(cls, v: int) -> int:
        current = date.today().year
        if v < current:
            raise ValueError(
                f"사업 연도({v})가 현재 연도({current}) 미만입니다."
            )
        return v
