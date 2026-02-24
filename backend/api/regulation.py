"""법령 검색 API — /api/regulation."""

from __future__ import annotations

from fastapi import APIRouter

from backend.services.search_service import search_service

router = APIRouter(prefix="/api/regulation", tags=["regulation"])


@router.get("/search")
async def search_regulations(q: str, scope: str = "all", limit: int = 20):
    """법령 검색."""
    results = await search_service.search_regulations(
        query=q, scope=scope, limit=limit
    )
    return {"query": q, "results": results, "count": len(results)}
