"""민원 API — /api/complaint."""

from __future__ import annotations

import structlog
from fastapi import APIRouter

from backend.ai.client import GptOssClient
from backend.ai.model_registry import ModelRegistry
from backend.config import settings
from backend.models.document import ComplaintRequest
from backend.services.hwpx_service import hwpx_service

router = APIRouter(prefix="/api/complaint", tags=["complaint"])
log = structlog.get_logger()

_client = GptOssClient(settings.OLLAMA_BASE_URL, settings.OLLAMA_MODEL)
_registry = ModelRegistry(settings.OLLAMA_BASE_URL)


@router.post("/classify")
async def classify_complaint(complaint_text: str):
    """민원 유형 분류."""
    await _registry.refresh()
    resolved, _ = _registry.select(task="classify", env=settings.environment)
    messages = [
        {
            "role": "user",
            "content": (
                "다음 민원을 분류하세요. 유형: 단순질의, 민원처리, 이의신청, 건의, 기타\n\n"
                f"민원 내용:\n{complaint_text}\n\n"
                "JSON 형식으로 응답: {\"type\": \"유형\", \"urgency\": \"high|medium|low\", \"summary\": \"요약\"}"
            ),
        }
    ]
    result = await _client.chat(messages=messages, task="classify", model=resolved)
    return {"classification": result["content"]}


@router.post("/draft")
async def draft_complaint_response(req: ComplaintRequest):
    """민원 답변 초안."""
    await _registry.refresh()
    resolved, _ = _registry.select(task="complaint_resp", env=settings.environment)
    messages = [
        {
            "role": "user",
            "content": (
                "다음 민원에 대한 공식 답변서 초안을 작성하세요.\n\n"
                f"민원 내용:\n{req.complaint_text}\n\n"
                "답변 형식: 1) 접수 확인 2) 검토 내용 3) 처리 결과 4) 불복 안내"
            ),
        }
    ]
    ai_result = await _client.chat(messages=messages, task="complaint_resp", model=resolved)
    response = ai_result["content"]

    # HWPX 생성
    if req.output_path:
        fields = {
            "민원내용": req.complaint_text[:200],
            "답변본문": response,
            "담당자": "",
        }
        result = hwpx_service.create_from_template(
            template_name="민원답변", fields=fields, output_path=req.output_path
        )
        log.info("민원 답변 생성", action="complaint_draft")
        return {"content": response, "path": str(result), "success": True}

    return {"content": response, "success": True}
