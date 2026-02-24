"""PII 탐지·마스킹 서비스 (7종 패턴)."""

from __future__ import annotations

import re
from pathlib import Path

import structlog

from backend.services.hwpx_service import hwpx_service

log = structlog.get_logger()

PII_PATTERNS: dict[str, re.Pattern] = {
    "주민등록번호": re.compile(r"\b\d{6}[-–]\d{7}\b"),
    "전화번호": re.compile(r"\b0\d{1,2}[-–. ]?\d{3,4}[-–. ]?\d{4}\b"),
    "이메일": re.compile(
        r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Z|a-z]{2,}\b"
    ),
    "주소": re.compile(
        r"(서울|경기|인천|부산|대구|광주|대전|울산|세종).*?"
        r"(동|읍|면|리)\s*\d+"
    ),
    "계좌번호": re.compile(
        r"\b\d{3,4}[-–]\d{2,6}[-–]\d{2,6}(?:[-–]\d{1,3})?\b"
    ),
    "여권번호": re.compile(r"\b[A-Z]{1,2}\d{7,9}\b"),
    "운전면허번호": re.compile(r"\b\d{2}[-–]\d{2}[-–]\d{6}[-–]\d{2}\b"),
}

MASK_CHAR = "●"


class PiiService:
    """PII 탐지 및 마스킹."""

    def scan(self, text: str, pii_types: list[str] | None = None) -> dict:
        """텍스트에서 PII 탐지."""
        patterns = {
            k: v for k, v in PII_PATTERNS.items() if not pii_types or k in pii_types
        }

        found: dict[str, list[dict]] = {}
        for name, pattern in patterns.items():
            matches = list(pattern.finditer(text))
            if matches:
                found[name] = [
                    {"start": m.start(), "end": m.end(), "value_length": len(m.group())}
                    for m in matches
                ]

        total = sum(len(v) for v in found.values())
        return {
            "passed": total == 0,
            "total_found": total,
            "found": found,
        }

    def mask(
        self, text: str, pii_types: list[str] | None = None
    ) -> str:
        """PII 마스킹."""
        patterns = {
            k: v for k, v in PII_PATTERNS.items() if not pii_types or k in pii_types
        }
        for _name, pattern in patterns.items():
            text = pattern.sub(lambda m: MASK_CHAR * len(m.group()), text)
        return text

    async def scan_file(self, path: str, pii_types: list[str] | None = None) -> dict:
        """파일에서 PII 탐지."""
        p = Path(path)
        if p.suffix.lower() == ".hwpx":
            text = hwpx_service.read_text(p)
        elif p.suffix.lower() in (".txt", ".md"):
            text = p.read_text(encoding="utf-8", errors="replace")
        else:
            return {"error": f"지원하지 않는 형식: {p.suffix}"}

        result = self.scan(text, pii_types)
        result["path"] = str(p)
        # RULE-07: 문서 내용은 절대 로그에 기록하지 않음
        log.info(
            "PII 스캔",
            action="pii_scan",
            path=str(p),
            found_count=result["total_found"],
        )
        return result

    async def mask_file(self, path: str, pii_types: list[str] | None = None) -> dict:
        """파일 PII 마스킹 (HWPX 파일은 새 파일 생성)."""
        p = Path(path)
        if p.suffix.lower() != ".hwpx":
            return {"error": "HWPX 파일만 마스킹 가능합니다"}

        text = hwpx_service.read_text(p)
        scan = self.scan(text, pii_types)

        if scan["passed"]:
            return {"path": str(p), "masked": False, "message": "PII 없음"}

        masked_text = self.mask(text, pii_types)
        output_path = p.parent / f"{p.stem}_masked{p.suffix}"
        hwpx_service.create(output_path, masked_text)

        return {
            "path": str(output_path),
            "masked": True,
            "pii_count": scan["total_found"],
        }


pii_service = PiiService()
