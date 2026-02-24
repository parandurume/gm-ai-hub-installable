"""사회연대경제 관련 Pydantic 모델."""

from __future__ import annotations

from pydantic import BaseModel, Field


class SocialEconomyAnalysis(BaseModel):
    """사회연대경제 분석 결과."""

    region: str = Field("", description="분석 지역")
    summary: str = Field("", description="분석 요약")
    enterprises_count: int = Field(0, description="기업 수")
    key_findings: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
