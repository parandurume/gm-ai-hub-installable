"""설정 API — /api/settings."""

from __future__ import annotations

from fastapi import APIRouter

from backend.config import settings
from backend.db.database import get_db

router = APIRouter(prefix="/api/settings", tags=["settings"])


@router.get("")
async def get_settings():
    """설정 조회."""
    # DB에서 저장된 설정
    saved = {}
    async with get_db() as db:
        async with db.execute("SELECT key, value FROM settings") as cursor:
            async for row in cursor:
                saved[row["key"]] = row["value"]

    return {
        "environment": settings.environment,
        "working_dir": str(settings.WORKING_DIR),
        "ollama_url": saved.get("ollama_url", settings.OLLAMA_BASE_URL),
        "ollama_model": saved.get("ollama_model", settings.OLLAMA_MODEL),
        "department_name": saved.get("department_name", ""),
        "officer_name": saved.get("officer_name", ""),
        "watch_paths": settings.watch_paths_list,
        "pii_scan_on_export": settings.PII_SCAN_ON_EXPORT,
        "saved": saved,
    }


@router.put("")
async def update_settings(updates: dict[str, str]):
    """설정 저장."""
    async with get_db() as db:
        for key, value in updates.items():
            await db.execute(
                "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
                (key, value),
            )
    return {"success": True, "updated": list(updates.keys())}
