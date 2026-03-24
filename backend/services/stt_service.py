"""STT 서비스 — faster-whisper 기반 로컬 음성 인식.

faster-whisper는 openai-whisper보다 4배 빠르고 메모리 효율이 높다.
모델은 첫 호출 시 HuggingFace Hub에서 자동으로 다운로드된다.

  - medium 모델: ~1.5 GB, 한국어 정확도 양호
  - large-v3 모델: ~3 GB, 최고 정확도

모든 처리는 로컬 CPU에서 수행 — 음성 데이터가 외부로 전송되지 않는다.

수동 모델 경로:
  자동 다운로드가 불가능한 환경(예: 오프라인 PC, 프록시 차단)에서는
  모델 폴더를 수동으로 복사한 뒤 설정에서 경로를 지정할 수 있다.
  설정 키: stt_model_path  (예: C:\\models\\faster-whisper-medium)
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
    """faster-whisper 래퍼 (lazy-load).

    model_path가 설정되면 HuggingFace 자동 다운로드 대신
    해당 로컬 디렉터리에서 모델을 로드한다.
    """

    def __init__(
        self,
        model_size: WhisperModelSize = _DEFAULT_MODEL,
        model_path: str | None = None,
    ) -> None:
        self._model_size = model_size
        self._model_path = model_path  # 수동 모델 폴더 경로
        self._model = None  # first-call lazy load

    def set_model_path(self, path: str | None) -> None:
        """수동 모델 경로 변경. 기존 로드된 모델은 해제된다."""
        if path != self._model_path:
            self._model_path = path
            self._model = None

    def _get_model(self):
        if self._model is None:
            try:
                from faster_whisper import WhisperModel  # noqa: PLC0415
            except ImportError as exc:
                raise RuntimeError(
                    "음성 인식 모듈을 불러올 수 없습니다. "
                    "앱을 재설치하거나 관리자에게 문의하세요."
                ) from exc

            # 수동 경로가 있으면 해당 경로에서 로드
            model_id = self._model_path or self._model_size
            log.info("STT 모델 로드 중", model=model_id)
            self._model = WhisperModel(
                model_id,
                device="cpu",
                compute_type="int8",  # CPU에서 메모리 효율 최대화
            )
            log.info("STT 모델 로드 완료", model=model_id)
        return self._model

    def is_model_cached(self) -> bool:
        """STT 모델이 로컬에 있는지 확인.

        수동 경로가 설정되어 있으면 해당 폴더 존재 여부를 확인한다.
        그렇지 않으면 HuggingFace 캐시 디렉터리를 확인한다.
        """
        try:
            if self._model_path:
                p = Path(self._model_path)
                # CTranslate2 모델: model.bin 파일이 있어야 유효
                return p.is_dir() and (p / "model.bin").exists()

            hf_home = os.environ.get("HF_HOME") or os.environ.get("HUGGINGFACE_HUB_CACHE")
            cache_base = Path(hf_home) if hf_home else Path.home() / ".cache" / "huggingface" / "hub"
            model_dir = cache_base / f"models--Systran--faster-whisper-{self._model_size}"
            return model_dir.exists()
        except Exception:
            return False

    @staticmethod
    def validate_model_path(path: str) -> tuple[bool, str]:
        """수동 모델 경로가 유효한지 확인. Returns (valid, message)."""
        p = Path(path)
        if not p.exists():
            return False, f"경로가 존재하지 않습니다: {path}"
        if not p.is_dir():
            return False, f"디렉터리가 아닙니다: {path}"
        if not (p / "model.bin").exists():
            return False, f"model.bin 파일이 없습니다. CTranslate2 형식의 faster-whisper 모델 폴더를 지정하세요."
        return True, "유효한 모델 경로입니다."

    def transcribe(self, audio_bytes: bytes, language: str = _DEFAULT_LANGUAGE) -> str:
        """오디오 바이트 → 텍스트 변환.

        CPU-bound 작업이므로 호출자는 asyncio.get_event_loop().run_in_executor()
        를 통해 스레드 풀에서 실행해야 한다.
        """
        model = self._get_model()

        # "auto" → None (faster-whisper는 None일 때 자동 감지)
        lang = None if language == "auto" else language

        # faster-whisper는 파일 경로를 요구하므로 임시 파일 사용
        suffix = ".webm"  # MediaRecorder 기본 포맷; wav/mp3/m4a도 동작
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(audio_bytes)
            tmp_path = tmp.name

        try:
            segments, info = model.transcribe(
                tmp_path,
                language=lang,
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
