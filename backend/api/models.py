"""모델 관리 API — /api/models (v1.2)."""

from __future__ import annotations

import asyncio
import json

import httpx
import structlog
from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from backend.ai.model_profiles import BUILTIN_PROFILES
from backend.ai.model_registry import ENVIRONMENT_DEFAULTS, ModelRegistry
from backend.config import settings
from backend.db.database import get_db

router = APIRouter(prefix="/api/models", tags=["models"])
log = structlog.get_logger()

_registry = ModelRegistry(settings.OLLAMA_BASE_URL)


@router.get("")
async def list_models():
    """설치된 모델 목록 + 프로파일."""
    await _registry.refresh()
    models = _registry.get_available_models()
    return {
        "models": models,
        "current_env": settings.environment,
        "recommended_default": ENVIRONMENT_DEFAULTS.get(
            settings.environment, {}
        ).get("default", "gpt-oss:20b"),
    }


@router.get("/recommend")
async def recommend_model(task: str, env: str | None = None):
    """태스크별 추천 모델."""
    await _registry.refresh()
    target_env = env or settings.environment
    model_id, use_thinking = _registry.select(
        task=task, env=target_env, reasoning="high"
    )
    profile = _registry.get_profile(model_id)
    return {
        "task": task,
        "env": target_env,
        "recommended_model": model_id,
        "use_thinking": use_thinking,
        "profile": profile.to_dict() if profile else None,
    }


@router.get("/pull-stream")
async def pull_model_stream(model: str):
    """ollama pull 스트리밍 진행률 SSE.

    Ollama의 /api/pull은 줄바꿈 구분 JSON 진행률 청크를 반환한다.
    이를 Server-Sent Events(SSE)로 그대로 포워딩한다.
    각 이벤트 형식: {"status":"...", "completed":N, "total":N}
    완료 시: data: [DONE]
    """
    log.info("모델 풀 스트림 요청", model=model)

    async def event_stream():
        try:
            async with httpx.AsyncClient(timeout=600) as c:
                async with c.stream(
                    "POST",
                    f"{settings.OLLAMA_BASE_URL}/api/pull",
                    json={"name": model},
                ) as r:
                    async for line in r.aiter_lines():
                        if line.strip():
                            yield f"data: {line}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/usage")
async def model_usage():
    """모델별 사용 통계."""
    async with get_db() as db:
        stats = []
        async with db.execute(
            "SELECT model, task, COUNT(*) as count, "
            "AVG(duration_ms) as avg_duration, "
            "SUM(tokens) as total_tokens "
            "FROM model_usage "
            "GROUP BY model, task "
            "ORDER BY count DESC"
        ) as cursor:
            async for row in cursor:
                stats.append({
                    "model": row["model"],
                    "task": row["task"],
                    "count": row["count"],
                    "avg_duration_ms": round(row["avg_duration"] or 0),
                    "total_tokens": row["total_tokens"] or 0,
                })
    return {"usage": stats}
