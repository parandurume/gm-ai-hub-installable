"""MIPROv2 최적화 관리 API — /api/optimize (v1.1)."""

from __future__ import annotations

import asyncio

import structlog
from fastapi import APIRouter

from backend.ai.optimization.scheduler import check_optimization_needed
from backend.db.database import get_db

router = APIRouter(prefix="/api/optimize", tags=["optimize"])
log = structlog.get_logger()

_running_task: asyncio.Task | None = None


@router.get("/status")
async def optimization_status():
    """파이프라인별 최적화 현황."""
    pipelines = []
    for name in ["docent", "gianmun", "complaint", "meeting"]:
        check = await check_optimization_needed(name)

        # 최근 최적화 정보
        async with get_db() as db:
            async with db.execute(
                "SELECT model, val_score, last_optimized_at "
                "FROM optimization_history WHERE pipeline = ? "
                "ORDER BY last_optimized_at DESC LIMIT 1",
                (name,),
            ) as cursor:
                row = await cursor.fetchone()

        pipelines.append({
            "name": name,
            "last_optimized": row["last_optimized_at"] if row else None,
            "model": row["model"] if row else None,
            "val_score": row["val_score"] if row else None,
            "new_docs_since": check.get("new_doc_count", 0),
            "optimization_recommended": check.get("needed", False),
            "reason": check.get("reason", ""),
        })

    return {"pipelines": pipelines}


@router.post("/run")
async def run_optimization(
    pipeline: str,
    model: str = "qwen3:32b",
    num_trials: int = 15,
):
    """최적화 실행 (비동기)."""
    global _running_task
    if _running_task and not _running_task.done():
        return {"error": "이미 최적화 진행 중입니다", "running": True}

    async def _run():
        from backend.ai.optimization.miprov2_runner import run_optimization

        result = await run_optimization(
            pipeline_name=pipeline, model=model, num_trials=num_trials
        )
        if result:
            _, meta = result
            async with get_db() as db:
                await db.execute(
                    "INSERT INTO optimization_history "
                    "(pipeline, model, val_score, num_trials, train_examples, save_path) "
                    "VALUES (?, ?, ?, ?, ?, ?)",
                    (
                        pipeline,
                        model,
                        meta["val_score"],
                        meta["num_trials"],
                        meta["train_examples"],
                        meta["save_path"],
                    ),
                )

    _running_task = asyncio.create_task(_run())
    return {"started": True, "pipeline": pipeline, "model": model}


@router.post("/reload")
async def reload_optimized():
    """최적화 파일 핫 리로드."""
    from backend.ai.dspy_config import load_optimized_pipeline
    from backend.ai.pipelines import (
        AiDocentPlanPipeline,
        ComplaintDraftPipeline,
        GianmunBodyPipeline,
        MeetingSummaryPipeline,
    )

    results = {}
    for name, cls in [
        ("docent", AiDocentPlanPipeline),
        ("gianmun", GianmunBodyPipeline),
        ("complaint", ComplaintDraftPipeline),
        ("meeting", MeetingSummaryPipeline),
    ]:
        pipeline = cls()
        loaded = load_optimized_pipeline(pipeline, name, "qwen3:32b")
        results[name] = "loaded" if loaded else "not_found"

    return {"reloaded": results}


@router.get("/history")
async def optimization_history():
    """최적화 이력."""
    async with get_db() as db:
        rows = []
        async with db.execute(
            "SELECT * FROM optimization_history ORDER BY last_optimized_at DESC LIMIT 50"
        ) as cursor:
            async for row in cursor:
                rows.append(dict(row))
    return {"history": rows}
