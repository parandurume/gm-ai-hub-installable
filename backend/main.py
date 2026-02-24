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

from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

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


if __name__ == "__main__":
    start()
