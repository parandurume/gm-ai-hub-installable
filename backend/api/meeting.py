"""회의록 API — /api/meeting."""

from __future__ import annotations

import structlog
from fastapi import APIRouter

from backend.ai.client import GptOssClient
from backend.ai.model_registry import ModelRegistry
from backend.config import settings
from backend.models.document import MeetingRequest
from backend.services.hwpx_service import hwpx_service

router = APIRouter(prefix="/api/meeting", tags=["meeting"])
log = structlog.get_logger()

_client = GptOssClient(settings.OLLAMA_BASE_URL, settings.OLLAMA_MODEL)
_registry = ModelRegistry(settings.OLLAMA_BASE_URL)


@router.post("/create")
async def create_meeting(req: MeetingRequest):
    """회의록 HWPX 생성."""
    # AI 정리 필요 시
    summary = req.content
    if len(req.content) > 500:
        await _registry.refresh()
        resolved, _ = _registry.select(task="meeting_minutes", env=settings.environment)
        messages = [
            {
                "role": "user",
                "content": (
                    f"다음 회의 내용을 공문서 형식 회의록으로 정리하세요.\n\n"
                    f"회의명: {req.title}\n참석자: {req.attendees}\n\n"
                    f"내용:\n{req.content}"
                ),
            }
        ]
        ai_result = await _client.chat(messages=messages, task="meeting_minutes", model=resolved)
        summary = ai_result["content"]

    fields = {
        "회의명": req.title,
        "일시": req.meeting_date,
        "참석자": req.attendees,
        "내용": summary,
        "장소": req.location,
        "결정사항": req.decisions,
        "후속조치": req.action_items,
    }

    output = req.output_path or str(
        settings.WORKING_DIR / f"회의록_{req.title}.hwpx"
    )
    result = hwpx_service.create_from_template(
        template_name="회의록", fields=fields, output_path=output
    )

    log.info("회의록 생성", action="create_meeting")
    return {"path": str(result), "success": True}
