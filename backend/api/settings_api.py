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
        "org_name": saved.get("org_name", ""),
        "department_name": saved.get("department_name", ""),
        "officer_name": saved.get("officer_name", ""),
        "watch_paths": settings.watch_paths_list,
        "pii_scan_on_export": settings.PII_SCAN_ON_EXPORT,
        "stt_model": saved.get("stt_model", "medium"),
        "stt_language": saved.get("stt_language", "ko"),
        "meeting_save_dir": saved.get("meeting_save_dir", ""),
        "saved": saved,
    }


# 프론트엔드가 전체 settings 객체를 보내므로 저장 불필요한 키를 제외
_READONLY_KEYS = {"environment", "watch_paths", "pii_scan_on_export", "saved"}


@router.put("")
async def update_settings(updates: dict):
    """설정 저장."""
    async with get_db() as db:
        saved_keys = []
        for key, value in updates.items():
            if key in _READONLY_KEYS or value is None:
                continue
            str_value = str(value) if not isinstance(value, str) else value
            await db.execute(
                "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
                (key, str_value),
            )
            saved_keys.append(key)
    return {"success": True, "updated": saved_keys}
