"""PII API — /api/pii."""

from __future__ import annotations

import tempfile
from datetime import datetime
from pathlib import Path

import structlog
from fastapi import APIRouter
from fastapi.responses import FileResponse
from pydantic import BaseModel

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


class PiiTextScanBody(BaseModel):
    text: str
    pii_types: list[str] | None = None


@router.post("/scan-text")
async def scan_text(body: PiiTextScanBody):
    """텍스트에서 PII를 스캔한다 (파일 경로 없이)."""
    result = pii_service.scan(body.text, body.pii_types)
    findings = _flatten_findings(result.get("found", {}), body.text)
    return {
        "passed": result["passed"],
        "total_found": result["total_found"],
        "findings": findings,
    }


@router.post("/mask")
async def mask_pii(body: PiiScanBody):
    """PII 마스킹."""
    return await pii_service.mask_file(body.path, body.pii_types)


class ExportReportBody(BaseModel):
    path: str
    findings: list[dict]
    total_found: int
    scan_date: str | None = None


@router.post("/export-report")
async def export_report(body: ExportReportBody):
    """PII 검사 보고서를 HWPX로 내보내기."""
    from backend.services.hwpx_service import hwpx_service

    filename = Path(body.path).name
    scan_date = body.scan_date or datetime.now().strftime("%Y-%m-%d %H:%M")

    lines = [
        "# PII 검사 보고서\n",
        f"- 파일: {filename}",
        f"- 검사일: {scan_date}",
        f"- 발견 건수: {body.total_found}건\n",
        "## 발견 내역\n",
        "| 유형 | 위치 | 길이 |",
        "|------|------|------|",
    ]
    for f in body.findings:
        lines.append(f"| {f.get('type', '-')} | {f.get('start', '-')} | {f.get('length', '-')} |")

    lines.append("")
    lines.append("## 조치 권고\n")
    lines.append("위 개인정보를 마스킹하거나 삭제한 후 문서를 배포하세요.")

    md = "\n".join(lines)
    title = f"PII검사보고서_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    tmp = Path(tempfile.mkdtemp()) / f"{title}.hwpx"
    hwpx_service.create(tmp, md)
    log.info("PII 보고서 내보내기", action="pii_export_report", findings=body.total_found)

    return FileResponse(
        path=tmp,
        filename=f"{title}.hwpx",
        media_type="application/vnd.hancom.hwpx",
    )


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
