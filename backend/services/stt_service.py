"""STT 서비스 — faster-whisper 기반 로컬 음성 인식.

faster-whisper는 openai-whisper보다 4배 빠르고 메모리 효율이 높다.
모델은 첫 호출 시 HuggingFace Hub에서 자동으로 다운로드된다.

  - medium 모델: ~1.5 GB, 한국어 정확도 양호
  - large-v3 모델: ~3 GB, 최고 정확도

모든 처리는 로컬 CPU에서 수행 — 음성 데이터가 외부로 전송되지 않는다.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Literal

import structlog

log = structlog.get_logger()

WhisperModelSize = Literal["tiny", "base", "small", "medium", "large-v2", "large-v3"]

_DEFAULT_MODEL: WhisperModelSize = "medium"
_DEFAULT_LANGUAGE = "ko"


class SttService:
    """faster-whisper 래퍼 (lazy-load)."""

    def __init__(self, model_size: WhisperModelSize = _DEFAULT_MODEL) -> None:
        self._model_size = model_size
        self._model = None  # first-call lazy load

    def _get_model(self):
        if self._model is None:
            try:
                from faster_whisper import WhisperModel  # noqa: PLC0415
            except ImportError as exc:
                raise RuntimeError(
                    "faster-whisper가 설치되어 있지 않습니다. "
                    "'pip install faster-whisper' 를 실행하세요."
                ) from exc

            log.info("STT 모델 로드 중", model=self._model_size)
            self._model = WhisperModel(
                self._model_size,
                device="cpu",
                compute_type="int8",  # CPU에서 메모리 효율 최대화
            )
            log.info("STT 모델 로드 완료", model=self._model_size)
        return self._model

    def is_model_cached(self) -> bool:
        """STT 모델이 로컬 HuggingFace 캐시에 있는지 확인.

        모델이 없으면 첫 transcribe 호출 시 ~1.5 GB 다운로드가 발생한다.
        """
        try:
            hf_home = os.environ.get("HF_HOME") or os.environ.get("HUGGINGFACE_HUB_CACHE")
            cache_base = Path(hf_home) if hf_home else Path.home() / ".cache" / "huggingface" / "hub"
            model_dir = cache_base / f"models--Systran--faster-whisper-{self._model_size}"
            return model_dir.exists()
        except Exception:
            return False

    def transcribe(self, audio_bytes: bytes, language: str = _DEFAULT_LANGUAGE) -> str:
        """오디오 바이트 → 텍스트 변환.

        CPU-bound 작업이므로 호출자는 asyncio.get_event_loop().run_in_executor()
        를 통해 스레드 풀에서 실행해야 한다.
        """
        model = self._get_model()

        # faster-whisper는 파일 경로를 요구하므로 임시 파일 사용
        suffix = ".webm"  # MediaRecorder 기본 포맷; wav/mp3/m4a도 동작
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(audio_bytes)
            tmp_path = tmp.name

        try:
            segments, info = model.transcribe(
                tmp_path,
                language=language,
                beam_size=5,
                vad_filter=True,  # 무음 구간 자동 제거
                vad_parameters={"min_silence_duration_ms": 500},
            )
            text = " ".join(seg.text.strip() for seg in segments)
            log.info(
                "음성 인식 완료",
                language=info.language,
                duration=round(info.duration, 1),
                chars=len(text),
            )
            return text.strip()
        finally:
            Path(tmp_path).unlink(missing_ok=True)


# 싱글턴 — 모델을 한 번만 로드
stt_service = SttService()
