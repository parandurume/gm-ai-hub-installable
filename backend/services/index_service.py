"""FTS5 인덱싱 서비스."""

from __future__ import annotations

import hashlib
from pathlib import Path

import structlog

from backend.config import settings
from backend.db.database import get_db
from backend.services.hwpx_service import hwpx_service

log = structlog.get_logger()


class IndexService:
    """FTS5 전문 검색 인덱스 관리."""

    async def index_file(self, path: str) -> dict:
        """단일 파일 인덱싱."""
        p = Path(path)
        if not p.exists():
            return {"error": "파일을 찾을 수 없습니다"}

        text = self._extract_text(p)
        text_hash = hashlib.sha256(text.encode()).hexdigest()

        async with get_db() as db:
            # 기존 항목 확인
            async with db.execute(
                "SELECT text_hash FROM documents WHERE path = ?", (str(p),)
            ) as cursor:
                row = await cursor.fetchone()
                if row and row["text_hash"] == text_hash:
                    return {"path": str(p), "status": "unchanged"}

            # 문서 테이블 upsert
            await db.execute(
                "INSERT OR REPLACE INTO documents "
                "(path, filename, ext, size_bytes, text_hash) "
                "VALUES (?, ?, ?, ?, ?)",
                (str(p), p.name, p.suffix.lstrip("."), p.stat().st_size, text_hash),
            )

            # FTS5 upsert
            await db.execute(
                "DELETE FROM documents_fts WHERE path = ?", (str(p),)
            )
            if text.strip():
                await db.execute(
                    "INSERT INTO documents_fts (path, filename, content) "
                    "VALUES (?, ?, ?)",
                    (str(p), p.name, text),
                )

        return {"path": str(p), "status": "indexed"}

    async def prune_stale(self) -> int:
        """디스크에 없는 파일의 DB 항목 제거."""
        removed = 0
        async with get_db() as db:
            async with db.execute("SELECT id, path FROM documents") as cursor:
                rows = await cursor.fetchall()
            for row in rows:
                if not Path(row["path"]).exists():
                    await db.execute("DELETE FROM documents WHERE id = ?", (row["id"],))
                    await db.execute("DELETE FROM documents_fts WHERE path = ?", (row["path"],))
                    removed += 1
                    log.info("스테일 항목 제거", path=row["path"])
        return removed

    async def rebuild_index(self, folder: str | None = None) -> dict:
        """전체 인덱스 재구축 (스테일 항목 정리 포함)."""
        # 1) 디스크에 없는 항목 정리
        pruned = await self.prune_stale()

        # 2) 새 파일 인덱싱
        base = Path(folder) if folder else Path(settings.WORKING_DIR)
        if not base.exists():
            return {"error": f"디렉토리 없음: {base}", "pruned": pruned}

        indexed = 0
        errors = 0
        exts = {".hwpx", ".hwp", ".pdf", ".docx", ".txt", ".md"}

        for p in base.rglob("*"):
            if not p.is_file() or p.suffix.lower() not in exts:
                continue
            try:
                result = await self.index_file(str(p))
                if "error" not in result:
                    indexed += 1
            except Exception as e:
                log.warning("인덱싱 오류", path=str(p), error=str(e))
                errors += 1

        return {"indexed": indexed, "errors": errors, "pruned": pruned, "base": str(base)}

    async def index_embedding(
        self, doc_path: str, chunk_text: str, chunk_index: int, vector: list[float]
    ) -> None:
        """임베딩 벡터 저장."""
        import json

        async with get_db() as db:
            async with db.execute(
                "SELECT id FROM documents WHERE path = ?", (doc_path,)
            ) as cursor:
                row = await cursor.fetchone()
                if not row:
                    return

            await db.execute(
                "INSERT INTO embeddings (doc_id, chunk_text, chunk_index, vector_json) "
                "VALUES (?, ?, ?, ?)",
                (row["id"], chunk_text, chunk_index, json.dumps(vector)),
            )

    @staticmethod
    def _extract_text(path: Path) -> str:
        ext = path.suffix.lower()
        if ext == ".hwpx":
            return hwpx_service.read_text(path)
        elif ext in (".txt", ".md"):
            return path.read_text(encoding="utf-8", errors="replace")
        elif ext == ".pdf":
            try:
                import fitz

                doc = fitz.open(str(path))
                return "\n".join(page.get_text() for page in doc)
            except ImportError:
                return ""
        elif ext == ".docx":
            try:
                from docx import Document

                doc = Document(str(path))
                return "\n".join(p.text for p in doc.paragraphs)
            except ImportError:
                return ""
        return ""


index_service = IndexService()
