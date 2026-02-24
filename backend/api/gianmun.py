"""기안문 API — /api/gianmun."""

from __future__ import annotations

import structlog
from fastapi import APIRouter
from fastapi.responses import StreamingResponse

import json

from backend.ai.client import GptOssClient
from backend.ai.guards import BudgetValidator, DateGuard
from backend.ai.model_registry import ModelRegistry
from backend.config import settings
from backend.models.document import (
    AiBodyRequest,
    Annotation,
    GianmunRequest,
    GianmunSaveRequest,
    GianmunValidateRequest,
)
from backend.services.hwpx_service import hwpx_service
from backend.services.pii_service import pii_service
from backend.services.web_fetch_service import (
    build_augmented_instruction,
    extract_urls,
    fetch_all_urls,
)

router = APIRouter(prefix="/api/gianmun", tags=["gianmun"])
log = structlog.get_logger()

_client = GptOssClient(settings.OLLAMA_BASE_URL, settings.OLLAMA_MODEL)
_registry = ModelRegistry(settings.OLLAMA_BASE_URL)

# 7종 템플릿
TEMPLATES = [
    {"name": "일반기안", "description": "일반 기안문"},
    {"name": "협조전", "description": "타 부서/기관 협조 요청"},
    {"name": "보고서", "description": "업무 보고서"},
    {"name": "계획서", "description": "사업 계획서"},
    {"name": "결과보고서", "description": "사업 결과 보고서"},
    {"name": "회의록", "description": "회의 회의록"},
    {"name": "민원답변", "description": "민원 답변서"},
]


@router.get("/templates")
async def list_templates():
    """템플릿 목록 (7종)."""
    return {"templates": TEMPLATES}


@router.post("/generate")
async def generate_gianmun(req: GianmunRequest):
    """기안문 생성 (AI 선택)."""
    body = req.body_text
    if req.ai_instruction and not body:
        # Registry-based model resolution
        await _registry.refresh()
        resolved, _ = _registry.select(task="gianmun_body", env=settings.environment)
        messages = [
            {"role": "user", "content": req.ai_instruction},
        ]
        result = await _client.chat(
            messages=messages,
            task="gianmun_body",
            system_extra=f"\n문서 종류: {req.doc_type}\n제목: {req.subject}",
            model=resolved,
        )
        body = result["content"]

    fields = {
        "제목": req.subject,
        "수신": req.recipients,
        "본문": body or "",
        "첨부": req.attachments,
    }

    result = hwpx_service.create_from_template(
        template_name=req.doc_type,
        fields=fields,
        output_path=req.output_path or str(
            settings.WORKING_DIR / f"{req.subject}.hwpx"
        ),
    )

    log.info("기안문 생성", action="create_gianmun", doc_type=req.doc_type)
    return {"path": str(result), "success": True, "doc_type": req.doc_type}


@router.post("/ai-body")
async def generate_ai_body(req: AiBodyRequest):
    """AI 본문만 생성 (SSE 스트리밍, JSON 이벤트). URL이 포함되면 웹 콘텐츠를 가져와 참조."""
    await _registry.refresh()
    resolved, _ = _registry.select(
        task="gianmun_body", env=settings.environment, user_override=req.model,
    )

    # URL 감지 → 웹 콘텐츠 가져오기
    urls = extract_urls(req.instruction)
    fetched_pages: list[dict] = []
    if urls:
        fetched_pages = await fetch_all_urls(req.instruction)

    instruction = build_augmented_instruction(req.instruction, fetched_pages)
    messages = [{"role": "user", "content": instruction}]

    async def stream():
        # URL을 가져왔으면 fetching 이벤트 전송
        for page in fetched_pages:
            status = page["title"] or page["url"]
            if page["error"]:
                status = f"{page['url']} (실패: {page['error']})"
            yield f"data: {json.dumps({'type': 'fetching', 'url': page['url'], 'status': status}, ensure_ascii=False)}\n\n"

        async for event in _client.stream(messages=messages, task="gianmun_body", model=resolved):
            yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
        yield f"data: {json.dumps({'type': 'done'})}\n\n"

    return StreamingResponse(stream(), media_type="text/event-stream")


def _detect_budget_table(text: str) -> dict | None:
    """마크다운 예산 테이블을 휴리스틱으로 파싱. 없으면 None."""
    import re as _re

    lines = text.split("\n")
    header_idx = None
    for i, line in enumerate(lines):
        if "|" in line and ("예산" in line or "금액" in line or "항목" in line):
            header_idx = i
            break
    if header_idx is None:
        return None

    # 구분자 행 건너뛰기
    data_start = header_idx + 2
    items: list[dict] = []
    total = 0
    amount_re = _re.compile(r"[\d,]+")
    for line in lines[data_start:]:
        if "|" not in line:
            break
        cells = [c.strip() for c in line.split("|") if c.strip()]
        if len(cells) < 2:
            continue
        # 마지막 숫자 셀을 금액으로
        for cell in reversed(cells):
            nums = amount_re.findall(cell.replace(",", ""))
            if nums:
                amt = int(nums[-1])
                items.append({"category": cells[0], "total_krw": amt})
                total += amt
                break

    if not items:
        return None
    return {"total_krw": total, "items": items}


@router.post("/validate")
async def validate_gianmun(req: GianmunValidateRequest):
    """텍스트 검증: DateGuard, PII, 예산."""
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

    # 3. Budget (옵셔널)
    budget_result = None
    budget_data = _detect_budget_table(text)
    if budget_data:
        budget_result = BudgetValidator.validate(
            total_krw=budget_data["total_krw"],
            items=budget_data["items"],
        )
        if not budget_result["valid"]:
            for issue in budget_result["issues"]:
                annotations.append(Annotation(
                    type="budget", subtype="validation",
                    start=0, end=0, severity="warning",
                    message=issue,
                ))

    annotations.sort(key=lambda a: a.start)

    return {
        "date_guard": date_guard,
        "pii": pii_result,
        "budget": budget_result,
        "annotations": [a.model_dump() for a in annotations],
    }


@router.post("/save")
async def save_gianmun(req: GianmunSaveRequest):
    """HWPX 저장."""
    fields = {"제목": req.subject, "수신": req.recipients, "본문": req.body}
    result = hwpx_service.create_from_template(
        template_name=req.doc_type,
        fields=fields,
        output_path=req.output_path or str(
            settings.WORKING_DIR / f"{req.subject}.hwpx"
        ),
    )
    return {"path": str(result), "success": True}
