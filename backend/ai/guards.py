"""
DateGuard  : AI 생성 텍스트에서 과거 연도 탐지·차단
BudgetValidator : 예산 합리성 검증
"""

from __future__ import annotations

import re
from datetime import date


class DateGuard:
    @classmethod
    def current_year(cls) -> int:
        return date.today().year

    @classmethod
    def scan(cls, text: str) -> dict:
        """텍스트에서 구식 연도(현재 연도 미만) 탐지."""
        year = cls.current_year()
        pattern = re.compile(r"(?<!\d)(20[0-9]{2})(?!\d)")
        all_years = [int(y) for y in pattern.findall(text)]
        stale = [y for y in all_years if y < year]
        return {
            "passed": len(stale) == 0,
            "stale_years": list(set(stale)),
            "current_year": year,
            "message": (
                "통과"
                if not stale
                else f"구식 연도 발견: {set(stale)}. {year}년 이상으로 수정 필요."
            ),
        }

    @classmethod
    def fix(cls, text: str) -> str:
        """구식 연도를 현재 연도로 자동 교체 (후처리용)."""
        year = cls.current_year()
        pattern = re.compile(r"(?<!\d)(20[012][0-9])(?!\d)")

        def replace(m: re.Match) -> str:
            y = int(m.group(1))
            return str(year) if y < year else m.group(1)

        return pattern.sub(replace, text)


class BudgetValidator:
    SCALE_RANGES = {
        "소규모": (1_000_000, 50_000_000),
        "중규모": (50_000_000, 200_000_000),
        "대규모": (200_000_000, 2_000_000_000),
    }

    @classmethod
    def validate(
        cls, total_krw: int, items: list[dict], scale: str = "소규모"
    ) -> dict:
        issues = []
        min_b, max_b = cls.SCALE_RANGES.get(scale, (0, float("inf")))

        # 총액 범위 검증
        if not (min_b <= total_krw <= max_b):
            issues.append(
                f"총액({total_krw:,}원)이 {scale} 범위({min_b:,}~{max_b:,}원) 밖"
            )

        # 항목 합계 일치 검증
        item_total = sum(i.get("total_krw", 0) for i in items)
        if item_total and abs(item_total - total_krw) > 10_000:
            issues.append(
                f"항목 합계({item_total:,}원) ≠ 총액({total_krw:,}원)"
            )

        # 인건비 비율 검증
        personnel = sum(
            i.get("total_krw", 0)
            for i in items
            if "인건비" in i.get("category", "") or "강사" in i.get("category", "")
        )
        if total_krw and personnel / total_krw > 0.75:
            issues.append(
                f"인건비 비율 {personnel / total_krw:.0%} 과도 (권장 75% 이하)"
            )

        return {"valid": len(issues) == 0, "issues": issues}
