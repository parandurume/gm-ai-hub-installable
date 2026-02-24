"""문서 비교 서비스 — 텍스트 diff + 수치 비교."""

from __future__ import annotations

import difflib
import re
from pathlib import Path

from backend.services.hwpx_service import hwpx_service


class DiffService:
    """두 문서의 텍스트·수치 비교."""

    async def compare(self, path_a: str, path_b: str) -> dict:
        """두 문서 비교."""
        text_a = self._get_text(path_a)
        text_b = self._get_text(path_b)

        lines_a = text_a.splitlines(keepends=True)
        lines_b = text_b.splitlines(keepends=True)

        diff = list(difflib.unified_diff(
            lines_a, lines_b,
            fromfile=Path(path_a).name,
            tofile=Path(path_b).name,
            lineterm="",
        ))

        # 통계
        added = sum(1 for line in diff if line.startswith("+") and not line.startswith("+++"))
        removed = sum(1 for line in diff if line.startswith("-") and not line.startswith("---"))

        # 수치 비교
        numbers_a = self._extract_numbers(text_a)
        numbers_b = self._extract_numbers(text_b)
        number_changes = self._compare_numbers(numbers_a, numbers_b)

        # 유사도
        similarity = difflib.SequenceMatcher(None, text_a, text_b).ratio()

        return {
            "path_a": path_a,
            "path_b": path_b,
            "diff_lines": diff,
            "added": added,
            "removed": removed,
            "similarity": round(similarity, 3),
            "number_changes": number_changes,
        }

    @staticmethod
    def _get_text(path: str) -> str:
        p = Path(path)
        if p.suffix.lower() == ".hwpx":
            return hwpx_service.read_text(p)
        elif p.suffix.lower() in (".txt", ".md"):
            return p.read_text(encoding="utf-8", errors="replace")
        return ""

    @staticmethod
    def _extract_numbers(text: str) -> list[tuple[str, float]]:
        """텍스트에서 숫자(금액 등) 추출."""
        pattern = re.compile(r"[\d,]+(?:\.\d+)?(?:원|만원|억원|백만원)?")
        results = []
        for m in pattern.finditer(text):
            raw = m.group()
            numeric = raw.replace(",", "").rstrip("원만억백")
            try:
                val = float(numeric)
                if "억" in raw:
                    val *= 100_000_000
                elif "만" in raw:
                    val *= 10_000
                elif "백만" in raw:
                    val *= 1_000_000
                results.append((raw, val))
            except ValueError:
                pass
        return results

    @staticmethod
    def _compare_numbers(
        nums_a: list[tuple[str, float]], nums_b: list[tuple[str, float]]
    ) -> list[dict]:
        """수치 변화 감지."""
        changes = []
        vals_a = {raw: val for raw, val in nums_a}
        vals_b = {raw: val for raw, val in nums_b}

        for raw_b, val_b in vals_b.items():
            # 동일 텍스트가 a에 없으면 new
            if raw_b not in vals_a:
                # 유사 값 찾기
                closest = min(
                    vals_a.values(),
                    key=lambda v: abs(v - val_b),
                    default=None,
                )
                if closest is not None and closest != val_b:
                    diff_pct = ((val_b - closest) / closest * 100) if closest else 0
                    changes.append({
                        "before": closest,
                        "after": val_b,
                        "diff_pct": round(diff_pct, 1),
                    })
        return changes


diff_service = DiffService()
