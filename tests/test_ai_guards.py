"""DateGuard + BudgetValidator 단위 테스트."""

from datetime import date

import pytest

from backend.ai.guards import BudgetValidator, DateGuard


class TestDateGuard:
    def test_current_year(self):
        assert DateGuard.current_year() == date.today().year

    def test_scan_passes_current_year(self):
        year = date.today().year
        result = DateGuard.scan(f"{year}년도 사업 계획")
        assert result["passed"] is True

    def test_scan_detects_stale_year(self):
        result = DateGuard.scan("2023년 사업보고서를 제출합니다.")
        assert result["passed"] is False
        assert 2023 in result["stale_years"]

    def test_scan_no_years(self):
        result = DateGuard.scan("사업 보고서를 제출합니다.")
        assert result["passed"] is True

    def test_scan_multiple_stale(self):
        result = DateGuard.scan("2022년과 2024년 실적")
        assert result["passed"] is False
        assert len(result["stale_years"]) >= 1

    def test_fix_replaces_stale(self):
        year = date.today().year
        fixed = DateGuard.fix("2023년 사업 계획")
        assert str(year) in fixed
        assert "2023" not in fixed

    def test_fix_keeps_current(self):
        year = date.today().year
        text = f"{year}년 사업 계획"
        assert DateGuard.fix(text) == text


class TestBudgetValidator:
    def test_valid_budget(self):
        result = BudgetValidator.validate(
            total_krw=10_000_000,
            items=[
                {"category": "인건비", "total_krw": 5_000_000},
                {"category": "운영비", "total_krw": 3_000_000},
                {"category": "교육비", "total_krw": 2_000_000},
            ],
            scale="소규모",
        )
        assert result["valid"] is True

    def test_total_out_of_range(self):
        result = BudgetValidator.validate(
            total_krw=500_000,
            items=[{"category": "운영비", "total_krw": 500_000}],
            scale="소규모",
        )
        assert result["valid"] is False
        assert any("범위" in i for i in result["issues"])

    def test_items_sum_mismatch(self):
        result = BudgetValidator.validate(
            total_krw=10_000_000,
            items=[
                {"category": "인건비", "total_krw": 3_000_000},
                {"category": "운영비", "total_krw": 2_000_000},
            ],
            scale="소규모",
        )
        assert result["valid"] is False
        assert any("합계" in i for i in result["issues"])

    def test_personnel_ratio_warning(self):
        result = BudgetValidator.validate(
            total_krw=10_000_000,
            items=[
                {"category": "인건비", "total_krw": 8_000_000},
                {"category": "운영비", "total_krw": 2_000_000},
            ],
            scale="소규모",
        )
        assert result["valid"] is False
        assert any("인건비" in i for i in result["issues"])
