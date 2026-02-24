"""헬스 체크 엔드포인트."""

from __future__ import annotations

import httpx
from fastapi import APIRouter

from backend.config import settings

router = APIRouter(prefix="/api", tags=["health"])


@router.get("/health")
async def health():
    """서버 상태 (Ollama 포함)."""
    ollama_ok = False
    ollama_models = []
    try:
        async with httpx.AsyncClient(timeout=5) as c:
            r = await c.get(f"{settings.OLLAMA_BASE_URL}/api/tags")
            if r.status_code == 200:
                ollama_ok = True
                ollama_models = [
                    m["name"] for m in r.json().get("models", [])
                ]
    except Exception:
        pass

    return {
        "status": "ok",
        "version": "2.0.0",
        "environment": settings.environment,
        "ollama": {
            "connected": ollama_ok,
            "url": settings.OLLAMA_BASE_URL,
            "models": ollama_models,
        },
        "hwp_tier": settings.hwp_tier,
        "working_dir": str(settings.WORKING_DIR),
    }


@router.get("/health/ollama")
async def health_ollama():
    """Ollama 모델 목록."""
    try:
        async with httpx.AsyncClient(timeout=10) as c:
            r = await c.get(f"{settings.OLLAMA_BASE_URL}/api/tags")
            return r.json()
    except Exception as e:
        return {"error": str(e), "models": []}
