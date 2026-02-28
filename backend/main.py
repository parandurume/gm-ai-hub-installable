"""
GM-AI-Hub FastAPI 애플리케이션 진입점.

시작 순서:
  1. 설정 로드 (.env)
  2. DB 초기화 (SQLite + FTS5)
  3. 폴더 감시 시작 (watchdog)
  4. gpt-oss 연결 확인
  5. 프론트엔드 정적 파일 서빙
  6. API 라우터 등록
"""

from __future__ import annotations

import os
import sys

# Windows: pipes/no-console 환경에서 cp1252 → UTF-8 강제 (structlog 한글 출력 보호)
if sys.stdout is None:
    sys.stdout = open(os.devnull, "w", encoding="utf-8")  # noqa: SIM115
elif hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
if sys.stderr is None:
    sys.stderr = open(os.devnull, "w", encoding="utf-8")  # noqa: SIM115
elif hasattr(sys.stderr, "reconfigure"):
    try:
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from contextlib import asynccontextmanager
from urllib.parse import urlparse

import structlog
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from backend import paths
from backend.api.router import register_routes
from backend.config import settings
from backend.db.database import init_db

log = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 시작
    log.info("GM-AI-Hub 시작", version="2.0.0", env=settings.APP_ENV)
    settings.ensure_directories()
    await init_db()

    # 폴더 감시 (watchdog)
    if settings.watch_paths_list:
        try:
            from backend.services.watcher_service import start_watcher

            await start_watcher(settings.WATCH_PATHS)
        except ImportError:
            log.warning("watcher_service 미구현, 폴더 감시 건너뜀")

    yield
    # 종료
    log.info("GM-AI-Hub 종료")


app = FastAPI(
    title="GM-AI-Hub API",
    version="2.0.0",
    lifespan=lifespan,
    docs_url="/api/docs" if settings.APP_DEBUG else None,
)

# ── Origin 검증 미들웨어 (CSRF 방어) ─────────────────────────
_SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}
ALLOWED_ORIGINS = {
    f"http://127.0.0.1:{settings.APP_PORT}",
    f"http://localhost:{settings.APP_PORT}",
    "http://127.0.0.1:5173",
    "http://localhost:5173",
}


class OriginCheckMiddleware(BaseHTTPMiddleware):
    """POST/PUT/DELETE 요청의 Origin 헤더를 검증한다.

    Origin이 없는 요청(curl, Postman 등)은 허용 — 브라우저 CSRF만 방어.
    """

    async def dispatch(self, request: Request, call_next):
        if request.method not in _SAFE_METHODS:
            origin = request.headers.get("origin") or request.headers.get("referer", "")
            if origin and "://" in origin:
                parsed = urlparse(origin)
                origin = f"{parsed.scheme}://{parsed.netloc}"
            if origin and origin not in ALLOWED_ORIGINS:
                log.warning("Origin 차단", origin=origin, path=request.url.path)
                return JSONResponse({"detail": "Origin not allowed"}, status_code=403)
        return await call_next(request)


app.add_middleware(OriginCheckMiddleware)

register_routes(app)

# 정적 파일 (프론트엔드 빌드 결과)
_frontend_dist = paths.frontend_dist()
if (_frontend_dist / "assets").exists():
    app.mount("/assets", StaticFiles(directory=str(_frontend_dist / "assets")))


@app.get("/{full_path:path}")
async def serve_spa(full_path: str):
    """모든 경로를 React SPA로 라우팅."""
    index = _frontend_dist / "index.html"
    if index.exists():
        return FileResponse(str(index))
    return {"message": "GM-AI-Hub API", "docs": "/api/docs"}


def start():
    import uvicorn

    if paths.is_frozen():
        uvicorn.run(
            app,
            host=settings.APP_HOST,
            port=settings.APP_PORT,
            reload=False,
        )
    else:
        uvicorn.run(
            "backend.main:app",
            host=settings.APP_HOST,
            port=settings.APP_PORT,
            reload=settings.APP_DEBUG,
        )


def download_stt_model():
    """STT 모델 가중치를 HuggingFace Hub에서 다운로드."""
    import sys

    print("STT 음성 인식 모델 다운로드 중... (약 1.5 GB, 인터넷 필요)", flush=True)
    try:
        from backend.services.stt_service import SttService

        SttService()._get_model()
        print("STT 모델 다운로드 완료.", flush=True)
    except Exception as exc:
        print(f"다운로드 실패: {exc}", flush=True)
        sys.exit(1)


if __name__ == "__main__":
    import sys

    if "--download-stt" in sys.argv:
        download_stt_model()
    else:
        start()
