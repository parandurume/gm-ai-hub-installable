"""과업지시서 API — /api/task-order."""

from __future__ import annotations

import json

import structlog
from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from backend.ai.client import GptOssClient
from backend.ai.guards import DateGuard
from backend.ai.model_registry import ModelRegistry
from backend.config import settings
from backend.db.database import get_setting
from backend.models.document import (
    Annotation,
    DraftValidateRequest,
    TaskOrderRequest,
    TaskOrderSaveRequest,
)
from backend.services.hwpx_service import hwpx_service
from backend.services.pii_service import pii_service

router = APIRouter(prefix="/api/task-order", tags=["task-order"])
log = structlog.get_logger()

_client = GptOssClient(settings.OLLAMA_BASE_URL, settings.OLLAMA_MODEL)
_registry = ModelRegistry(settings.OLLAMA_BASE_URL)


async def _load_user_context() -> tuple[str, str]:
    """DB에서 부서명·담당자명·기관명을 읽어 (system_extra, org_name) 반환."""
    org_name = await get_setting("org_name", "소속기관")
    dept = (await get_setting("department_name", "")).strip()
    officer = (await get_setting("officer_name", "")).strip()
    if not dept and not officer:
        return "", org_name
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
    return extra, org_name


# ── 과업지시서 전용 시스템 프롬프트 보충 ──────────────────────

_TASK_ORDER_SYSTEM_EXTRA = """
[과업지시서 작성 규칙]
- 과업지시서는 3개 섹션으로 구성합니다:
  1. 과업개요 (과업명, 과업목적, 과업기간/장소, 과업범위 및 주요내용, 소요예산)
  2. 과업수행 세부내용 (세부사업별 기획·홍보·운영 계획, 참여대상·인원, 성과물 제출)
  3. 과업수행에 관한 일반사항 (일반지침, 기타사항)
- 각 섹션 번호는 네모 박스 형태로 표기합니다: **1 과업개요**, **2 과업수행 세부내용**, **3 과업수행에 관한 일반사항**
- 하위 항목은 1. 2. 3. 순번, 가. 나. 다. 한글 순번, ❍ 기호를 사용합니다.
- "광명시"가 기관명으로 사용될 때 임의로 변경하지 마세요.
- "계약상대자"는 용역 수행자를 지칭하는 공식 표현입니다.
- 과업수행에 관한 일반사항 3절에는 표준 지침(감독관 협의, 점검 권한, 지적소유권, 비밀유지, 대금청구 등)을 포함합니다.
- 기타사항에는 전담인력 확보, 착수보고서 제출, 성과물 제출기한을 포함합니다.
"""


@router.post("/generate")
async def generate_task_order(req: TaskOrderRequest):
    """과업지시서 AI 생성 (SSE 스트리밍)."""
    await _registry.refresh()
    resolved, _ = _registry.select(
        task="task_order", env=settings.environment, user_override=req.model,
    )

    user_ctx, org_name = await _load_user_context()

    # 사용자 입력을 구조화된 프롬프트로 조합
    scope_text = ""
    if req.scope_items:
        _KO_ORDER = "가나다라마바사아자차카타파하"
        scope_text = "\n".join(f"  {_KO_ORDER[i] if i < len(_KO_ORDER) else chr(0xAC00 + i)}. {item}" for i, item in enumerate(req.scope_items))

    prompt_parts = [f"다음 정보를 바탕으로 과업지시서를 작성하세요.\n"]
    prompt_parts.append(f"과업명: {req.task_name}")
    if req.purpose:
        prompt_parts.append(f"과업목적: {req.purpose}")
    if req.period:
        prompt_parts.append(f"과업기간: {req.period}")
    if req.location:
        prompt_parts.append(f"과업장소: {req.location}")
    if req.budget:
        prompt_parts.append(f"소요예산: {req.budget}")
    if scope_text:
        prompt_parts.append(f"과업범위:\n{scope_text}")
    if req.details:
        prompt_parts.append(f"세부 지시사항:\n{req.details}")

    instruction = "\n".join(prompt_parts)
    messages = [{"role": "user", "content": instruction}]

    async def stream():
        async for event in _client.stream(
            messages=messages,
            task="task_order",
            model=resolved,
            org_name=org_name,
            system_extra=_TASK_ORDER_SYSTEM_EXTRA + user_ctx,
        ):
            yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
        yield f"data: {json.dumps({'type': 'done'})}\n\n"

    return StreamingResponse(stream(), media_type="text/event-stream")


@router.post("/save")
async def save_task_order(req: TaskOrderSaveRequest):
    """과업지시서 HWPX 저장."""
    fields = {"제목": req.task_name, "본문": req.body}
    result = hwpx_service.create_from_template(
        template_name="과업지시서",
        fields=fields,
        output_path=req.output_path or str(
            settings.WORKING_DIR / f"{req.task_name} 과업지시서.hwpx"
        ),
    )
    log.info("과업지시서 저장", action="save_task_order", task_name=req.task_name)
    return {"path": str(result), "success": True}


@router.post("/validate")
async def validate_task_order(req: DraftValidateRequest):
    """과업지시서 텍스트 검증: DateGuard, PII."""
    import re as _re

    text = req.text
    annotations: list[Annotation] = []

    # 1. DateGuard
    date_guard = DateGuard.scan(text)
    if not date_guard["passed"]:
        year_pat = _re.compile(r"(?<!\d)(20[0-9]{2})(?!\d)")
        current_year = DateGuard.current_year()
        for m in year_pat.finditer(text):
            if int(m.group(1)) < current_year:
                annotations.append(Annotation(
                    type="date", subtype="stale_year",
                    start=m.start(), end=m.end(), severity="warning",
                    message=f"구식 연도 {m.group(1)} → {current_year}년 권장",
                ))

    # 2. PII
    pii_result = pii_service.scan(text)
    for pii_type, matches in pii_result.get("found", {}).items():
        for match in matches:
            annotations.append(Annotation(
                type="pii", subtype=pii_type,
                start=match["start"], end=match["end"], severity="error",
                message=f"개인정보 ({pii_type}) 발견",
            ))

    annotations.sort(key=lambda a: a.start)

    return {
        "date_guard": date_guard,
        "pii": pii_result,
        "annotations": [a.model_dump() for a in annotations],
    }
