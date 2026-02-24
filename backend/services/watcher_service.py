"""폴더 감시 서비스 (watchdog)."""

from __future__ import annotations

import asyncio
from pathlib import Path

import structlog

log = structlog.get_logger()

_watcher_task: asyncio.Task | None = None
_observer = None


async def start_watcher(watch_paths: str) -> None:
    """폴더 감시 시작."""
    global _watcher_task

    paths = [p.strip() for p in watch_paths.split(",") if p.strip()]
    if not paths:
        return

    try:
        from watchdog.observers import Observer
        from watchdog.events import FileSystemEventHandler
    except ImportError:
        log.warning("watchdog 미설치, 폴더 감시 비활성화")
        return

    class FileHandler(FileSystemEventHandler):
        def __init__(self):
            self._loop = asyncio.get_event_loop()

        def on_created(self, event):
            if not event.is_directory:
                self._loop.call_soon_threadsafe(
                    asyncio.ensure_future, _on_file_change(event.src_path, "created")
                )

        def on_modified(self, event):
            if not event.is_directory:
                self._loop.call_soon_threadsafe(
                    asyncio.ensure_future, _on_file_change(event.src_path, "modified")
                )

        def on_deleted(self, event):
            if not event.is_directory:
                self._loop.call_soon_threadsafe(
                    asyncio.ensure_future, _on_file_change(event.src_path, "deleted")
                )

    global _observer
    _observer = Observer()
    handler = FileHandler()

    for p in paths:
        path = Path(p)
        if path.exists():
            _observer.schedule(handler, str(path), recursive=True)
            log.info("폴더 감시 시작", path=str(path))

    _observer.daemon = True
    _observer.start()


async def stop_watcher() -> None:
    """폴더 감시 중지."""
    global _observer
    if _observer:
        _observer.stop()
        _observer = None
        log.info("폴더 감시 중지")


async def _on_file_change(path: str, event_type: str) -> None:
    """파일 변경 이벤트 처리."""
    p = Path(path)
    supported = {".hwpx", ".hwp", ".pdf", ".docx", ".xlsx", ".txt", ".md"}
    if p.suffix.lower() not in supported:
        return

    log.info("파일 변경 감지", path=path, event=event_type)

    if event_type in ("created", "modified"):
        try:
            from backend.services.index_service import index_service

            await index_service.index_file(path)
        except Exception as e:
            log.warning("자동 인덱싱 실패", path=path, error=str(e))
