"""AI 채팅 API — /api/chat + WebSocket 스트리밍 + 이미지 분석."""

from __future__ import annotations

import base64
import json
import tempfile
import uuid
from datetime import datetime
from pathlib import Path

import aiosqlite
import structlog
from fastapi import APIRouter, File, Form, HTTPException, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from pydantic import BaseModel

from backend.ai.client import GptOssClient
from backend.ai.model_registry import ModelRegistry
from backend.config import settings
from backend.db.database import get_db, get_setting
from backend.models.document import ChatMessage
from backend.paths import chat_images_dir
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

MAX_IMAGE_SIZE = 10 * 1024 * 1024  # 10 MB
ALLOWED_MIME = {"image/jpeg", "image/png", "image/gif", "image/webp"}

_client = GptOssClient(settings.OLLAMA_BASE_URL, settings.OLLAMA_MODEL)
_registry = ModelRegistry(settings.OLLAMA_BASE_URL)


async def _load_image_b64(image_id: str) -> dict | None:
    """DB에서 이미지 경로 조회 후 base64로 변환."""
    async with get_db() as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT file_path, mime_type FROM chat_images WHERE id = ?", (image_id,)
        ) as cursor:
            row = await cursor.fetchone()
    if not row:
        return None
    p = Path(row["file_path"])
    if not p.exists():
        return None
    data = p.read_bytes()
    b64 = base64.b64encode(data).decode()
    return {"type": "image_url", "image_url": {"url": f"data:{row['mime_type']};base64,{b64}"}}


async def _build_vision_content(text: str, image_ids: list[str]) -> list[dict]:
    """텍스트 + 이미지 ID 목록 → OpenAI vision content 배열."""
    parts: list[dict] = []
    if text:
        parts.append({"type": "text", "text": text})
    for img_id in image_ids:
        part = await _load_image_b64(img_id)
        if part:
            parts.append(part)
    return parts


async def _expand_images_in_history(context: list[dict]) -> list[dict]:
    """history 메시지의 image_ids를 base64 content로 변환."""
    result = []
    for msg in context:
        img_ids = msg.get("image_ids") or []
        if img_ids:
            parts = await _build_vision_content(msg.get("content", ""), img_ids)
            result.append({"role": msg["role"], "content": parts if parts else msg.get("content", "")})
        else:
            result.append({"role": msg["role"], "content": msg.get("content", "")})
    return result


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


@router.post("/upload-image")
async def upload_image(
    file: UploadFile = File(...),
    session_id: int = Form(...),
):
    """이미지 업로드 → 디스크 저장 → ID 반환."""
    if file.content_type not in ALLOWED_MIME:
        raise HTTPException(400, f"지원하지 않는 이미지 형식: {file.content_type}")

    data = await file.read()
    if len(data) > MAX_IMAGE_SIZE:
        raise HTTPException(400, f"이미지 크기 제한 초과 (최대 {MAX_IMAGE_SIZE // 1024 // 1024}MB)")

    image_id = f"img_{uuid.uuid4().hex[:12]}"
    ext = file.filename.rsplit(".", 1)[-1].lower() if file.filename and "." in file.filename else "jpg"
    save_path = chat_images_dir() / f"{image_id}.{ext}"
    save_path.write_bytes(data)

    async with get_db() as db:
        await db.execute(
            "INSERT INTO chat_images (id, session_id, filename, mime_type, file_path, size_bytes) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (image_id, session_id, file.filename or "image", file.content_type, str(save_path), len(data)),
        )
        await db.commit()

    log.info("이미지 업로드", action="upload_image", image_id=image_id, size=len(data))
    return {"image_id": image_id, "filename": file.filename, "size_bytes": len(data)}


@router.get("/images/{image_id}")
async def get_image(image_id: str):
    """저장된 이미지 반환."""
    async with get_db() as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT file_path, mime_type, filename FROM chat_images WHERE id = ?", (image_id,)
        ) as cursor:
            row = await cursor.fetchone()
    if not row:
        raise HTTPException(404, "이미지를 찾을 수 없습니다")
    return FileResponse(row["file_path"], media_type=row["mime_type"], filename=row["filename"])


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

            # Frontend sends: message, model, reasoning_level, deep_mode, history, image_ids
            content = data.get("message", data.get("content", ""))
            user_model = data.get("model")  # null = auto select
            reasoning = data.get("reasoning_level", data.get("reasoning", "medium"))
            deep_mode = data.get("deep_mode", False)
            context = data.get("history", data.get("context", []))
            image_ids: list[str] = data.get("image_ids", [])

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

            # 이미지가 포함된 경우 vision content 형식으로 변환
            has_images = bool(image_ids)
            if has_images:
                user_content = await _build_vision_content(augmented, image_ids)
            else:
                user_content = augmented

            # history에 이미지가 포함된 메시지가 있으면 base64로 확장
            expanded_context = await _expand_images_in_history(context)
            messages = [*expanded_context, {"role": "user", "content": user_content}]

            # Registry model selection
            await _registry.refresh()
            resolved_model, use_thinking = _registry.select(
                task=task,
                env=settings.environment,
                user_override=user_model,
                reasoning=reasoning,
            )

            # 이미지 첨부 시 비전 모델 자동 전환
            if has_images:
                profile = _registry.get_profile(resolved_model)
                if not profile or not profile.supports_vision:
                    vision_model = _registry.select_vision()
                    if vision_model:
                        resolved_model = vision_model
                        use_thinking = False
                        await ws.send_json({"type": "model_switch", "model": vision_model})
                    else:
                        await ws.send_json({
                            "type": "error",
                            "message": "비전 모델이 설치되어 있지 않습니다. 터미널에서 'ollama pull llava' 등을 실행하세요.",
                        })
                        continue

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
    images: list[str] | None = None


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
            "SELECT id, role, content, thinking, images, created_at FROM chat_messages WHERE session_id = ? ORDER BY id",
            (session_id,),
        ) as cursor:
            rows = []
            async for row in cursor:
                d = dict(row)
                d["image_ids"] = json.loads(d.pop("images")) if d.get("images") else []
                rows.append(d)
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
    """세션 삭제 (CASCADE로 메시지도 삭제) + 이미지 파일 정리."""
    async with get_db() as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT file_path FROM chat_images WHERE session_id = ?", (session_id,)
        ) as cursor:
            paths = [row["file_path"] async for row in cursor]
        await db.execute("DELETE FROM chat_sessions WHERE id = ?", (session_id,))
        await db.commit()
    # 디스크에서 이미지 파일 삭제
    for p in paths:
        Path(p).unlink(missing_ok=True)
    return {"ok": True}


@router.post("/sessions/{session_id}/messages")
async def add_message(session_id: int, req: MessageCreate):
    """메시지 저장 + 세션 updated_at 갱신. 첫 user 메시지면 자동 제목 설정."""
    images_json = json.dumps(req.images) if req.images else None
    async with get_db() as db:
        await db.execute(
            "INSERT INTO chat_messages (session_id, role, content, thinking, images) VALUES (?, ?, ?, ?, ?)",
            (session_id, req.role, req.content, req.thinking, images_json),
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
