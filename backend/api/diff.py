"""문서 비교 API — /api/diff."""

from __future__ import annotations

from fastapi import APIRouter

from backend.models.document import DiffRequest
from backend.services.diff_service import diff_service

router = APIRouter(prefix="/api/diff", tags=["diff"])


@router.post("")
async def compare_documents(req: DiffRequest):
    """문서 비교."""
    return await diff_service.compare(req.path_a, req.path_b)
