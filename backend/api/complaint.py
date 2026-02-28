"""민원 API — /api/complaint."""

from __future__ import annotations

import structlog
from fastapi import APIRouter

from backend.ai.client import GptOssClient
from backend.ai.model_registry import ModelRegistry
from backend.config import settings
from backend.db.database import get_setting
from backend.models.document import ComplaintRequest
from backend.services.hwpx_service import hwpx_service

router = APIRouter(prefix="/api/complaint", tags=["complaint"])
log = structlog.get_logger()

_client = GptOssClient(settings.OLLAMA_BASE_URL, settings.OLLAMA_MODEL)
_registry = ModelRegistry(settings.OLLAMA_BASE_URL)


async def _load_user_context() -> tuple[str, str, str, str]:
    """(system_extra, org_name, dept, officer) — DB에서 부서명·담당자명 로드."""
    org_name = await get_setting("org_name", "소속기관")
    dept = (await get_setting("department_name", "")).strip()
    officer = (await get_setting("officer_name", "")).strip()
    if not dept and not officer:
        return "", org_name, dept, officer
    parts = []
    if dept:
        parts.append(f"- 부서: {dept}")
    if officer:
        parts.append(f"- 담당자: {officer}")
    extra = (
        "\n\n[사용자 정보]\n"
        + "\n".join(parts)
        + "\n문서 작성 시 위 부서명·담당자명을 그대로 사용하세요. 임의로 변경하거나 대체 이름을 만들지 마세요.\n"
    )
    return extra, org_name, dept, officer


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
    org_name = await get_setting("org_name", "소속기관")
    result = await _client.chat(messages=messages, task="classify", model=resolved, org_name=org_name)
    return {"classification": result["content"]}


@router.post("/draft")
async def draft_complaint_response(req: ComplaintRequest):
    """민원 답변 초안."""
    await _registry.refresh()
    resolved, _ = _registry.select(task="complaint_resp", env=settings.environment)
    user_ctx, org_name, _dept, officer = await _load_user_context()
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
    ai_result = await _client.chat(
        messages=messages, task="complaint_resp", model=resolved,
        org_name=org_name, system_extra=user_ctx,
    )
    response = ai_result["content"]

    # HWPX 생성
    if req.output_path:
        fields = {
            "민원내용": req.complaint_text[:200],
            "답변본문": response,
            "담당자": officer,
        }
        result = hwpx_service.create_from_template(
            template_name="민원답변", fields=fields, output_path=req.output_path
        )
        log.info("민원 답변 생성", action="complaint_draft")
        return {"content": response, "path": str(result), "success": True}

    return {"content": response, "success": True}
