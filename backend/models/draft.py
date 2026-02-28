"""공문서 초안(Draft) 관련 Pydantic 모델."""

from __future__ import annotations

from pydantic import BaseModel, Field


class DraftTemplate(BaseModel):
    """공문서 초안 템플릿 정보."""

    name: str
    description: str = ""
    required_fields: list[str] = Field(default_factory=list)
    optional_fields: list[str] = Field(default_factory=list)
    auto_fields: list[str] = Field(default_factory=list)


class DraftResult(BaseModel):
    """공문서 초안 생성 결과."""

    output_path: str
    template_used: str
    fields_filled: list[str]
    ai_generated: bool = False
