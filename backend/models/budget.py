"""예산 관련 Pydantic 모델 (RULE-03: Pydantic for outputs)."""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, Field, field_validator, model_validator


class BudgetItem(BaseModel):
    """예산 항목."""

    category: str = Field(..., description="비목 (예: 인건비, 운영비, 교육비)")
    unit: str = Field("식", description="단위 (예: 시간, 명, 식, 개)")
    quantity: int = Field(..., ge=1, description="수량")
    unit_price: int = Field(..., ge=0, description="단가(원)")
    total_krw: int = Field(..., ge=0, description="금액(원)")

    @model_validator(mode="after")
    def check_total(self) -> "BudgetItem":
        expected = self.quantity * self.unit_price
        if abs(self.total_krw - expected) > 100:
            raise ValueError(
                f"항목 금액 불일치: {self.quantity}×{self.unit_price:,}"
                f"={expected:,} ≠ {self.total_krw:,}"
            )
        return self


class BudgetBreakdown(BaseModel):
    """예산 내역서 (AI 출력 검증용)."""

    fiscal_year: int = Field(..., description="회계연도")
    total_krw: int = Field(..., gt=0, description="총액(원)")
    items: list[BudgetItem] = Field(..., min_length=1, description="예산 항목")
    scale: str = Field("소규모", description="사업 규모")

    @field_validator("fiscal_year")
    @classmethod
    def fiscal_year_not_stale(cls, v: int) -> int:
        current = date.today().year
        if v < current:
            raise ValueError(
                f"회계연도({v})가 현재 연도({current}) 미만입니다."
            )
        return v

    @model_validator(mode="after")
    def check_items_sum(self) -> "BudgetBreakdown":
        item_total = sum(item.total_krw for item in self.items)
        if abs(item_total - self.total_krw) > 10_000:
            raise ValueError(
                f"항목 합계({item_total:,}원) ≠ 총액({self.total_krw:,}원)"
            )
        return self
