"""Pydantic 모델 단위 테스트."""

from datetime import date

import pytest

from backend.models.budget import BudgetBreakdown, BudgetItem
from backend.models.timeline import DocumentTimeline, Phase


class TestBudgetItem:
    def test_valid_item(self):
        item = BudgetItem(
            category="인건비",
            unit="월",
            quantity=12,
            unit_price=3_000_000,
            total_krw=36_000_000,
        )
        assert item.total_krw == 36_000_000

    def test_total_mismatch_raises(self):
        with pytest.raises(ValueError, match="금액 불일치"):
            BudgetItem(
                category="인건비",
                unit="월",
                quantity=12,
                unit_price=3_000_000,
                total_krw=10_000_000,  # wrong
            )


class TestBudgetBreakdown:
    def test_valid_budget(self):
        year = date.today().year
        budget = BudgetBreakdown(
            fiscal_year=year,
            total_krw=10_000_000,
            items=[
                BudgetItem(
                    category="인건비", unit="월", quantity=5,
                    unit_price=1_000_000, total_krw=5_000_000,
                ),
                BudgetItem(
                    category="운영비", unit="식", quantity=5,
                    unit_price=1_000_000, total_krw=5_000_000,
                ),
            ],
        )
        assert budget.total_krw == 10_000_000

    def test_stale_year_raises(self):
        with pytest.raises(ValueError, match="현재 연도"):
            BudgetBreakdown(
                fiscal_year=2020,
                total_krw=10_000_000,
                items=[
                    BudgetItem(
                        category="운영비", unit="식", quantity=10,
                        unit_price=1_000_000, total_krw=10_000_000,
                    ),
                ],
            )

    def test_items_sum_mismatch_raises(self):
        year = date.today().year
        with pytest.raises(ValueError, match="합계"):
            BudgetBreakdown(
                fiscal_year=year,
                total_krw=20_000_000,
                items=[
                    BudgetItem(
                        category="인건비", unit="월", quantity=5,
                        unit_price=1_000_000, total_krw=5_000_000,
                    ),
                ],
            )


class TestDocumentTimeline:
    def test_valid_timeline(self):
        year = date.today().year
        tl = DocumentTimeline(
            year=year,
            title="AI 도슨트 사업",
            phases=[Phase(name="1단계", start_month="3월", end_month="6월")],
            total_months=9,
        )
        assert tl.year == year

    def test_stale_year_raises(self):
        with pytest.raises(ValueError, match="현재 연도"):
            DocumentTimeline(
                year=2020,
                title="테스트",
                phases=[Phase(name="1", start_month="1월", end_month="2월")],
                total_months=2,
            )
