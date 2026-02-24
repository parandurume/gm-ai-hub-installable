"""첫 실행 셋업 위저드 API — /api/setup."""

from __future__ import annotations

from pathlib import Path

import httpx
from fastapi import APIRouter
from pydantic import BaseModel

from backend.config import settings
from backend.db.database import get_db

router = APIRouter(prefix="/api/setup", tags=["setup"])

# Ollama에서 확인할 권장 모델 목록
RECOMMENDED_MODELS = [
    {"id": "gpt-oss:20b", "name": "GPT-OSS 20B", "description": "기본 텍스트 생성 모델", "required": True},
    {"id": "nomic-embed-text", "name": "Nomic Embed Text", "description": "문서 임베딩용", "required": False},
]


@router.get("/status")
async def setup_status():
    """셋업 완료 여부 확인."""
    async with get_db() as db:
        async with db.execute(
            "SELECT value FROM settings WHERE key = 'setup_completed'"
        ) as cursor:
            row = await cursor.fetchone()

    completed = row and row["value"] == "true" if row else False
    return {"setup_completed": completed}


@router.get("/check-ollama")
async def check_ollama():
    """Ollama 연결 상태 및 설치된 모델 확인."""
    ollama_url = settings.OLLAMA_BASE_URL
    result = {
        "connected": False,
        "url": ollama_url,
        "installed_models": [],
        "recommended_models": RECOMMENDED_MODELS,
        "missing_models": [],
    }

    try:
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get(f"{ollama_url}/api/tags")
            if resp.status_code == 200:
                result["connected"] = True
                data = resp.json()
                installed = [m["name"] for m in data.get("models", [])]
                result["installed_models"] = installed

                # 누락 모델 확인
                for rec in RECOMMENDED_MODELS:
                    # 정확한 이름 또는 태그 없는 이름으로 매칭
                    base_name = rec["id"].split(":")[0]
                    found = any(
                        m == rec["id"] or m.startswith(f"{base_name}:")
                        for m in installed
                    )
                    if not found:
                        result["missing_models"].append(rec)
    except Exception:
        pass

    return result


class SetupCompleteRequest(BaseModel):
    """셋업 완료 요청."""
    department_name: str = ""
    officer_name: str = ""
    ollama_url: str = "http://127.0.0.1:11434"
    ollama_model: str = "gpt-oss:20b"


@router.post("/complete")
async def complete_setup(req: SetupCompleteRequest):
    """셋업 완료 처리 — 설정 저장."""
    async with get_db() as db:
        pairs = {
            "setup_completed": "true",
            "department_name": req.department_name,
            "officer_name": req.officer_name,
            "ollama_url": req.ollama_url,
            "ollama_model": req.ollama_model,
        }
        for key, value in pairs.items():
            await db.execute(
                "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
                (key, value),
            )

    return {"success": True, "message": "초기 설정이 완료되었습니다."}
