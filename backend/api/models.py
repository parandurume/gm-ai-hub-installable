"""모델 관리 API — /api/models (v1.1)."""

from __future__ import annotations

import asyncio

import httpx
import structlog
from fastapi import APIRouter

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


@router.post("/pull")
async def pull_model(model: str):
    """ollama pull 실행."""
    log.info("모델 풀 요청", model=model)
    try:
        async with httpx.AsyncClient(timeout=600) as c:
            r = await c.post(
                f"{settings.OLLAMA_BASE_URL}/api/pull",
                json={"name": model},
            )
            return {"success": True, "model": model, "response": r.text[:500]}
    except Exception as e:
        return {"success": False, "model": model, "error": str(e)}


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
