"""SQLite 데이터베이스 초기화 및 연결 관리."""

from __future__ import annotations

import sqlite3
from contextlib import asynccontextmanager
from pathlib import Path

import aiosqlite
import structlog

from backend import paths
from backend.config import settings

log = structlog.get_logger()

_MIGRATIONS_DIR = paths.migrations_dir()


async def init_db() -> None:
    """DB 초기화: WAL 모드 설정 + 마이그레이션 실행."""
    settings.ensure_directories()
    db_path = str(settings.DB_PATH)

    async with aiosqlite.connect(db_path) as db:
        await db.execute("PRAGMA journal_mode=WAL")
        await db.execute("PRAGMA foreign_keys=ON")

        # 마이그레이션 실행
        await _run_migrations(db)
        await db.commit()

    log.info("DB 초기화 완료", path=db_path)


async def _run_migrations(db: aiosqlite.Connection) -> None:
    """migrations/ 디렉토리의 SQL 파일을 순서대로 실행."""
    # 마이그레이션 추적 테이블
    await db.execute(
        "CREATE TABLE IF NOT EXISTS _migrations ("
        "  name TEXT PRIMARY KEY, applied_at TEXT DEFAULT (datetime('now'))"
        ")"
    )

    applied = set()
    async with db.execute("SELECT name FROM _migrations") as cursor:
        async for row in cursor:
            applied.add(row[0])

    if not _MIGRATIONS_DIR.exists():
        return

    for sql_file in sorted(_MIGRATIONS_DIR.glob("*.sql")):
        if sql_file.name in applied:
            continue
        log.info("마이그레이션 실행", file=sql_file.name)
        sql = sql_file.read_text(encoding="utf-8")
        await db.executescript(sql)
        await db.execute(
            "INSERT INTO _migrations (name) VALUES (?)", (sql_file.name,)
        )


@asynccontextmanager
async def get_db():
    """비동기 DB 연결 컨텍스트 매니저."""
    db = await aiosqlite.connect(str(settings.DB_PATH))
    db.row_factory = aiosqlite.Row
    try:
        await db.execute("PRAGMA foreign_keys=ON")
        yield db
        await db.commit()
    except Exception:
        await db.rollback()
        raise
    finally:
        await db.close()


def get_db_sync() -> sqlite3.Connection:
    """동기 DB 연결 (스크립트 등에서 사용)."""
    conn = sqlite3.connect(str(settings.DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn
