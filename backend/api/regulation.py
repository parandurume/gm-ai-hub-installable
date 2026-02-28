"""법령 검색 API — /api/regulation."""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from backend.services.search_service import search_service

router = APIRouter(prefix="/api/regulation", tags=["regulation"])


class OcRequest(BaseModel):
    oc: str


@router.post("/oc")
async def set_oc(req: OcRequest):
    """세션 OC 설정 (메모리에만 저장, 앱 종료 시 소멸)."""
    from backend.services.law_api_service import set_session_oc

    set_session_oc(req.oc)
    return {"success": True}


@router.get("/search")
async def search_regulations(q: str, scope: str = "all", limit: int = 20):
    """법령 검색 — 온라인 우선, 오프라인 폴백."""
    source = "offline"
    try:
        from backend.services.law_api_service import LawApiUnavailable, law_api_service

        results = await law_api_service.search(query=q, limit=limit)
        source = "online"
    except Exception:
        results = await search_service.search_regulations(
            query=q, scope=scope, limit=limit
        )
        source = "offline"

    return {"query": q, "results": results, "count": len(results), "source": source}


@router.get("/status")
async def regulation_status():
    """법령 검색 소스 상태 (온라인/오프라인) + OC 설정 여부."""
    oc_set = False
    online = False
    try:
        from backend.services.law_api_service import get_session_oc, law_api_service

        oc_set = bool(get_session_oc())
        online = await law_api_service.is_available()
    except Exception:
        pass
    return {"online": online, "oc_set": oc_set}
