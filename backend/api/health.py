"""헬스 체크 엔드포인트."""

from __future__ import annotations

import asyncio
import os
import signal
import sys

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
        "version": "2.4.0",
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


@router.post("/quit")
async def quit_app():
    """앱 종료 — 서버 프로세스를 종료해 트레이도 연쇄 종료.

    Windows에서 SIGINT(GenerateConsoleCtrlEvent)는 CREATE_NO_WINDOW로 시작한
    콘솔 없는 프로세스에 전달되지 않는다. SIGTERM(TerminateProcess)을 사용한다.
    """

    async def _shutdown():
        await asyncio.sleep(0.3)
        # Windows: SIGTERM → TerminateProcess() (콘솔 불필요, 즉시 종료)
        # Linux/macOS: SIGINT → uvicorn 정상 종료
        sig = signal.SIGTERM if sys.platform == "win32" else signal.SIGINT
        os.kill(os.getpid(), sig)

    asyncio.create_task(_shutdown())
    return {"success": True}
