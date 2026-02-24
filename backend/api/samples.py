"""학습 샘플 관리 API — /api/samples."""

from __future__ import annotations

import structlog
from fastapi import APIRouter
from pydantic import BaseModel

from backend.services import sample_extract_service as svc

router = APIRouter(prefix="/api/samples", tags=["samples"])
log = structlog.get_logger()


class ExtractRequest(BaseModel):
    pipeline: str
    files: list[str] | None = None  # None → 전체 스캔


class ApproveRequest(BaseModel):
    pipeline: str
    examples: list[dict]


class RejectRequest(BaseModel):
    pipeline: str
    filenames: list[str] | None = None  # None → 전체 삭제


@router.get("/scan")
async def scan_samples(pipeline: str = "gianmun"):
    """샘플 폴더 스캔 → 파일 목록."""
    files = svc.scan_samples(pipeline)
    return {"pipeline": pipeline, "files": files, "count": len(files)}


@router.post("/extract")
async def extract_samples(req: ExtractRequest):
    """HWPX 파일 추출 + AI 분석 → 후보 예시."""
    candidates = await svc.extract_and_analyze(req.pipeline, req.files)
    ok = [c for c in candidates if "error" not in c]
    errors = [c for c in candidates if "error" in c]
    return {
        "pipeline": req.pipeline,
        "candidates": ok,
        "errors": errors,
        "total": len(candidates),
    }


@router.get("/pending")
async def get_pending(pipeline: str = "gianmun"):
    """대기 중인 후보 예시."""
    pending = svc.load_pending(pipeline)
    return {"pipeline": pipeline, "pending": pending, "count": len(pending)}


@router.post("/approve")
async def approve_examples(req: ApproveRequest):
    """검토 완료 예시 → 학습 데이터 저장."""
    result = svc.approve_examples(req.pipeline, req.examples)
    log.info("samples_approved", pipeline=req.pipeline, **result)
    return result


@router.delete("/reject")
async def reject_pending(req: RejectRequest):
    """대기 중인 후보 제거."""
    result = svc.reject_pending(req.pipeline, req.filenames)
    return result
