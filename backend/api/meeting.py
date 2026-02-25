"""회의록 API — /api/meeting."""

from __future__ import annotations

import asyncio

import structlog
from fastapi import APIRouter, File, HTTPException, UploadFile

from backend.ai.client import GptOssClient
from backend.ai.model_registry import ModelRegistry
from backend.config import settings
from backend.models.document import MeetingRequest
from backend.services.hwpx_service import hwpx_service

router = APIRouter(prefix="/api/meeting", tags=["meeting"])
log = structlog.get_logger()

_client = GptOssClient(settings.OLLAMA_BASE_URL, settings.OLLAMA_MODEL)
_registry = ModelRegistry(settings.OLLAMA_BASE_URL)


@router.get("/stt-status")
async def stt_status():
    """STT 모델 캐시 상태 확인.

    - available: faster-whisper 라이브러리가 설치되어 있는지 여부
    - cached: 모델 가중치가 로컬 캐시에 있어 즉시 사용 가능한지 여부
    - cached=false: 첫 사용 시 ~1.5 GB 다운로드 필요
    """
    from backend.services.stt_service import stt_service

    available = True
    try:
        import faster_whisper  # noqa: F401
    except ImportError:
        available = False

    return {
        "model": stt_service._model_size,
        "available": available,
        "cached": stt_service.is_model_cached() if available else False,
        "loaded": stt_service._model is not None,
    }


@router.post("/transcribe")
async def transcribe_audio(file: UploadFile = File(...)):
    """오디오 파일(webm/wav/mp3/m4a) → 텍스트 변환.

    faster-whisper로 로컬 처리 — 음성 데이터 외부 전송 없음.
    CPU-bound 작업이므로 스레드 풀 실행.
    """
    from backend.services.stt_service import stt_service

    audio_bytes = await file.read()
    if not audio_bytes:
        raise HTTPException(status_code=400, detail="빈 오디오 파일입니다.")

    try:
        loop = asyncio.get_event_loop()
        text = await loop.run_in_executor(None, stt_service.transcribe, audio_bytes)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    log.info("음성 인식 완료", action="transcribe", chars=len(text))
    return {"text": text}


@router.post("/create")
async def create_meeting(req: MeetingRequest):
    """회의록 AI 요약 및 HWPX 생성."""
    await _registry.refresh()
    resolved, _ = _registry.select(
        task="meeting_minutes",
        env=settings.environment,
        user_override=req.model,
    )

    # 내용이 충분하면 AI가 공문서 형식으로 정리
    if len(req.content.strip()) > 100:
        messages = [
            {
                "role": "user",
                "content": (
                    f"다음 회의 내용을 공문서 형식 회의록으로 정리하세요.\n\n"
                    f"회의명: {req.title}\n"
                    f"일시: {req.meeting_date}\n"
                    f"참석자: {req.attendees}\n\n"
                    f"내용:\n{req.content}"
                ),
            }
        ]
        ai_result = await _client.chat(
            messages=messages, task="meeting_minutes", model=resolved
        )
        summary = ai_result["content"]
        thinking = ai_result.get("thinking")
    else:
        summary = req.content
        thinking = None

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

    log.info("회의록 생성", action="create_meeting", model=resolved)
    return {
        "summary": summary,
        "thinking": thinking,
        "path": str(result),
        "success": True,
    }
