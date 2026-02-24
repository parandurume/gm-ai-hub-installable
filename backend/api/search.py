"""검색 API — /api/search."""

from __future__ import annotations

from fastapi import APIRouter

from backend.services.index_service import index_service
from backend.services.search_service import search_service

router = APIRouter(prefix="/api/search", tags=["search"])


@router.get("")
async def search_documents(
    q: str,
    mode: str = "keyword",
    limit: int = 20,
):
    """문서 검색 (keyword | semantic | hybrid)."""
    results = await search_service.search(query=q, mode=mode, limit=limit)
    return {"query": q, "mode": mode, "results": results, "count": len(results)}


@router.post("/index")
async def index_file(path: str):
    """특정 파일 인덱스 추가."""
    return await index_service.index_file(path)
