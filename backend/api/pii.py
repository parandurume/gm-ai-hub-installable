"""PII API — /api/pii."""

from __future__ import annotations

from pathlib import Path

import structlog
from fastapi import APIRouter

from backend.models.document import PiiBatchScanBody, PiiScanBody
from backend.services.pii_service import pii_service

router = APIRouter(prefix="/api/pii", tags=["pii"])
log = structlog.get_logger()


def _flatten_findings(found: dict, text: str | None = None) -> list[dict]:
    """found dict → 정렬된 flat findings 배열."""
    findings: list[dict] = []
    for pii_type, matches in found.items():
        for m in matches:
            entry = {
                "type": pii_type,
                "start": m["start"],
                "end": m["end"],
                "length": m["value_length"],
            }
            if text:
                entry["preview"] = text[m["start"]:m["end"]]
            findings.append(entry)
    findings.sort(key=lambda f: f["start"])
    return findings


@router.post("/scan")
async def scan_pii(body: PiiScanBody):
    """PII 탐지 (Pydantic body, include_text 지원)."""
    result = await pii_service.scan_file(body.path, body.pii_types)
    if "error" in result:
        return result

    text = None
    masked_text = None
    if body.include_text:
        p = Path(body.path)
        if p.suffix.lower() == ".hwpx":
            from backend.services.hwpx_service import hwpx_service
            text = hwpx_service.read_text(p)
        elif p.suffix.lower() in (".txt", ".md"):
            text = p.read_text(encoding="utf-8", errors="replace")
        if text:
            masked_text = pii_service.mask(text, body.pii_types)

    findings = _flatten_findings(result.get("found", {}), text)

    response = {
        "passed": result["passed"],
        "total_found": result["total_found"],
        "findings": findings,
        "path": result.get("path", body.path),
    }
    if body.include_text and text is not None:
        response["text"] = text
        response["masked_text"] = masked_text
    return response


@router.post("/mask")
async def mask_pii(body: PiiScanBody):
    """PII 마스킹."""
    return await pii_service.mask_file(body.path, body.pii_types)


@router.post("/batch-scan")
async def batch_scan_pii(body: PiiBatchScanBody):
    """여러 파일 일괄 PII 스캔."""
    results: list[dict] = []
    type_summary: dict[str, int] = {}
    total_files_with_pii = 0

    for path in body.paths:
        raw = await pii_service.scan_file(path, body.pii_types)
        if "error" in raw:
            results.append({"path": path, "error": raw["error"]})
            continue

        findings = _flatten_findings(raw.get("found", {}))
        if not raw["passed"]:
            total_files_with_pii += 1
        for pii_type, matches in raw.get("found", {}).items():
            type_summary[pii_type] = type_summary.get(pii_type, 0) + len(matches)

        results.append({
            "path": raw.get("path", path),
            "passed": raw["passed"],
            "total_found": raw["total_found"],
            "findings": findings,
        })

    return {
        "results": results,
        "total_files": len(body.paths),
        "files_with_pii": total_files_with_pii,
        "type_summary": type_summary,
    }
