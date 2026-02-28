"""AI 채팅 API — /api/chat + WebSocket 스트리밍."""

from __future__ import annotations

import json
import tempfile
from datetime import datetime
from pathlib import Path

import aiosqlite
import structlog
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from pydantic import BaseModel

from backend.ai.client import GptOssClient
from backend.ai.model_registry import ModelRegistry
from backend.config import settings
from backend.db.database import get_db, get_setting
from backend.models.document import ChatMessage
from backend.services.web_fetch_service import (
    build_augmented_prompt,
    extract_urls,
    fetch_all_urls,
)

router = APIRouter(prefix="/api/chat", tags=["chat"])
log = structlog.get_logger()

DEEP_MODE_PROMPT = """

[심층 분석 모드]
사용자의 요청을 받으면, 바로 답변하지 말고 다음 단계를 따르세요:

1단계 — 분석: 사용자의 요청에서 부족하거나 모호한 부분을 파악합니다.
2단계 — 질문: 더 좋은 답변을 위해 필요한 구체적인 질문 2~3개를 제시합니다.
  - 질문은 사용자의 요청 맥락에 맞는 실질적인 질문이어야 합니다.
  - 일반적이거나 뻔한 질문은 하지 마세요.
3단계 — 대기: 질문을 한 후, 사용자의 답변을 기다립니다.
4단계 — 답변: 사용자가 답변하면, 그 정보를 종합하여 포괄적이고 상세한 답변을 작성합니다.

이미 충분한 맥락이 있는 후속 메시지(질문에 대한 답변)라면 바로 4단계로 진행하세요.
"""

_client = GptOssClient(settings.OLLAMA_BASE_URL, settings.OLLAMA_MODEL)
_registry = ModelRegistry(settings.OLLAMA_BASE_URL)


async def _load_user_context() -> tuple[str, str]:
    """DB에서 부서명·담당자명·기관명을 읽어 (system_extra, org_name) 반환."""
    org_name = await get_setting("org_name", "소속기관")
    try:
        async with get_db() as db:
            async with db.execute(
                "SELECT key, value FROM settings WHERE key IN ('department_name', 'officer_name')"
            ) as cursor:
                rows = {row["key"]: row["value"] async for row in cursor}
        dept = rows.get("department_name", "").strip()
        officer = rows.get("officer_name", "").strip()
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
    except Exception:
        return "", org_name


@router.post("")
async def chat(msg: ChatMessage):
    """단일 메시지 (JSON 응답)."""
    await _registry.refresh()
    task = "plan_document" if msg.reasoning == "high" else "draft_body"
    resolved_model, use_thinking = _registry.select(
        task=task, env=settings.environment,
        user_override=msg.model, reasoning=msg.reasoning,
    )
    messages = [*msg.context, {"role": "user", "content": msg.content}]
    user_ctx, org_name = await _load_user_context()
    result = await _client.chat(
        messages=messages, task=task, model=resolved_model,
        system_extra=user_ctx, org_name=org_name,
    )
    # RULE-07: content 로그 금지
    log.info("채팅 응답", action="chat", model=result["model"], success=True)
    return {"content": result["content"], "thinking": result["thinking"], "model": result["model"]}


@router.websocket("/stream")
async def chat_stream(ws: WebSocket):
    """WebSocket 스트리밍 채팅 (모델 선택 + thinking 분리)."""
    from backend.main import ALLOWED_ORIGINS

    origin = ws.headers.get("origin", "")
    if origin and not any(origin.startswith(a) for a in ALLOWED_ORIGINS):
        await ws.close(code=4003, reason="Origin not allowed")
        return
    await ws.accept()

    try:
        while True:
            raw = await ws.receive_text()
            data = json.loads(raw)

            # Frontend sends: message, model, reasoning_level, deep_mode, history
            content = data.get("message", data.get("content", ""))
            user_model = data.get("model")  # null = auto select
            reasoning = data.get("reasoning_level", data.get("reasoning", "medium"))
            deep_mode = data.get("deep_mode", False)
            context = data.get("history", data.get("context", []))

            task = "plan_document" if reasoning == "high" else "draft_body"

            # URL detection → secure fetch → augment message
            urls = extract_urls(content)
            fetched_pages: list[dict] = []
            if urls:
                fetched_pages = await fetch_all_urls(content)
                for page in fetched_pages:
                    status = page.get("title") or page["url"]
                    if page["error"]:
                        status = f"{page['url']} (차단: {page['error']})"
                    await ws.send_json({"type": "fetching", "url": page["url"], "status": status})

            augmented = build_augmented_prompt(content, fetched_pages)
            messages = [*context, {"role": "user", "content": augmented}]

            # Registry model selection
            await _registry.refresh()
            resolved_model, use_thinking = _registry.select(
                task=task,
                env=settings.environment,
                user_override=user_model,
                reasoning=reasoning,
            )

            user_ctx, org_name = await _load_user_context()
            system_extra = (DEEP_MODE_PROMPT if deep_mode else "") + user_ctx

            try:
                full = ""
                full_thinking = ""
                async for event in _client.stream(
                    messages=messages, task=task,
                    system_extra=system_extra, model=resolved_model,
                    org_name=org_name,
                ):
                    if event["type"] == "thinking":
                        full_thinking += event["content"]
                        await ws.send_json({"type": "thinking", "content": event["content"]})
                    elif event["type"] == "token":
                        full += event["content"]
                        await ws.send_json({"type": "token", "content": event["content"]})

                await ws.send_json({
                    "type": "done",
                    "full_content": full,
                    "thinking": full_thinking or None,
                    "model": resolved_model,
                })
            except Exception as e:
                await ws.send_json({"type": "error", "message": str(e)})

    except WebSocketDisconnect:
        pass
    except Exception:
        pass


class SaveHwpxRequest(BaseModel):
    messages: list[dict]
    title: str = ""


@router.post("/save-hwpx")
async def save_chat_as_hwpx(req: SaveHwpxRequest):
    """대화 내용 → HWPX 파일 다운로드."""
    from backend.services.hwpx_service import hwpx_service

    lines: list[str] = []
    for msg in req.messages:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        if role == "user":
            lines.append(f"**[사용자]** {content}")
        else:
            lines.append(f"**[AI]** {content}")
        lines.append("")

    body = "\n".join(lines)
    title = req.title or f"채팅내용_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    filename = f"{title}.hwpx"

    # Generate to temp file, return as browser download
    tmp = Path(tempfile.mkdtemp()) / filename
    hwpx_service.create(tmp, f"# {title}\n\n{body}")
    log.info("채팅 HWPX 다운로드", action="chat_save_hwpx", messages=len(req.messages))

    return FileResponse(
        path=tmp,
        filename=filename,
        media_type="application/vnd.hancom.hwpx",
    )


# ── 채팅 세션 CRUD ──────────────────────────────────────────────


class SessionCreate(BaseModel):
    title: str = ""
    model: str | None = None


class MessageCreate(BaseModel):
    role: str
    content: str
    thinking: str | None = None


class SessionUpdate(BaseModel):
    title: str


@router.get("/sessions")
async def list_sessions():
    """채팅 세션 목록 (최신순, 최대 50개)."""
    async with get_db() as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """
            SELECT s.id, s.title, s.model, s.created_at, s.updated_at,
                   COUNT(m.id) AS message_count
            FROM chat_sessions s
            LEFT JOIN chat_messages m ON m.session_id = s.id
            GROUP BY s.id
            ORDER BY s.updated_at DESC
            LIMIT 50
            """
        ) as cursor:
            rows = [dict(row) async for row in cursor]
    return {"sessions": rows}


@router.post("/sessions")
async def create_session(req: SessionCreate):
    """새 채팅 세션 생성."""
    async with get_db() as db:
        cursor = await db.execute(
            "INSERT INTO chat_sessions (title, model) VALUES (?, ?)",
            (req.title, req.model),
        )
        await db.commit()
        session_id = cursor.lastrowid
    return {"id": session_id, "title": req.title}


@router.get("/sessions/{session_id}/messages")
async def get_session_messages(session_id: int):
    """세션의 메시지 목록."""
    async with get_db() as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT id, role, content, thinking, created_at FROM chat_messages WHERE session_id = ? ORDER BY id",
            (session_id,),
        ) as cursor:
            rows = [dict(row) async for row in cursor]
    return {"messages": rows}


@router.put("/sessions/{session_id}")
async def update_session(session_id: int, req: SessionUpdate):
    """세션 제목 수정."""
    async with get_db() as db:
        await db.execute(
            "UPDATE chat_sessions SET title = ?, updated_at = datetime('now', 'localtime') WHERE id = ?",
            (req.title, session_id),
        )
        await db.commit()
    return {"ok": True}


@router.delete("/sessions/{session_id}")
async def delete_session(session_id: int):
    """세션 삭제 (CASCADE로 메시지도 삭제)."""
    async with get_db() as db:
        await db.execute("DELETE FROM chat_sessions WHERE id = ?", (session_id,))
        await db.commit()
    return {"ok": True}


@router.post("/sessions/{session_id}/messages")
async def add_message(session_id: int, req: MessageCreate):
    """메시지 저장 + 세션 updated_at 갱신. 첫 user 메시지면 자동 제목 설정."""
    async with get_db() as db:
        await db.execute(
            "INSERT INTO chat_messages (session_id, role, content, thinking) VALUES (?, ?, ?, ?)",
            (session_id, req.role, req.content, req.thinking),
        )
        # 첫 user 메시지 → 자동 제목
        if req.role == "user":
            async with db.execute(
                "SELECT title FROM chat_sessions WHERE id = ?", (session_id,)
            ) as cursor:
                row = await cursor.fetchone()
            if row and not row[0]:
                title = req.content[:30].strip()
                if len(req.content) > 30:
                    title += "…"
                await db.execute(
                    "UPDATE chat_sessions SET title = ? WHERE id = ?",
                    (title, session_id),
                )
        await db.execute(
            "UPDATE chat_sessions SET updated_at = datetime('now', 'localtime') WHERE id = ?",
            (session_id,),
        )
        await db.commit()
    return {"ok": True}
