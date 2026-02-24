"""문서 관리 서비스 — CRUD, 목록, 메타데이터."""

from __future__ import annotations

import hashlib
from pathlib import Path

import structlog

from backend.config import settings
from backend.db.database import get_db
from backend.services.hwpx_service import hwpx_service

log = structlog.get_logger()

# 지원 형식
SUPPORTED_EXTS = {".hwpx", ".hwp", ".pdf", ".docx", ".xlsx", ".txt", ".md"}


class DocumentService:
    """파일 시스템 + DB 인덱스 기반 문서 관리."""

    async def list_documents(
        self,
        folder: str | None = None,
        ext_filter: str | None = None,
        recursive: bool = False,
    ) -> list[dict]:
        """파일 목록 조회."""
        base = Path(folder) if folder else Path(settings.WORKING_DIR)
        if not base.exists():
            return []

        pattern = "**/*" if recursive else "*"
        files = []
        for p in base.glob(pattern):
            if not p.is_file():
                continue
            if p.suffix.lower() not in SUPPORTED_EXTS:
                continue
            if ext_filter and p.suffix.lower() != f".{ext_filter}":
                continue
            files.append({
                "path": str(p),
                "filename": p.name,
                "ext": p.suffix.lstrip("."),
                "size_bytes": p.stat().st_size,
                "modified_at": p.stat().st_mtime,
            })
        return sorted(files, key=lambda f: f["modified_at"], reverse=True)

    async def get_metadata(self, path: str) -> dict:
        """파일 메타데이터 (DB + 파일 시스템)."""
        p = Path(path)
        if not p.exists():
            return {"error": "파일을 찾을 수 없습니다", "path": path}

        meta = {
            "path": str(p),
            "filename": p.name,
            "ext": p.suffix.lstrip("."),
            "size_bytes": p.stat().st_size,
        }

        if p.suffix.lower() == ".hwpx":
            hwpx_meta = hwpx_service.read_metadata(p)
            meta.update(hwpx_meta)

        # DB에서 추가 메타
        async with get_db() as db:
            async with db.execute(
                "SELECT * FROM documents WHERE path = ?", (str(p),)
            ) as cursor:
                row = await cursor.fetchone()
                if row:
                    meta["indexed_at"] = row["indexed_at"]
                    meta["text_hash"] = row["text_hash"]

        return meta

    async def get_text(self, path: str) -> str:
        """파일 텍스트 추출."""
        p = Path(path)
        ext = p.suffix.lower()

        if ext == ".hwpx":
            return hwpx_service.read_text(p)
        elif ext == ".txt" or ext == ".md":
            return p.read_text(encoding="utf-8", errors="replace")
        elif ext == ".pdf":
            return self._extract_pdf_text(p)
        elif ext == ".docx":
            return self._extract_docx_text(p)
        else:
            return f"[지원하지 않는 형식: {ext}]"

    async def get_preview(self, path: str) -> str:
        """HTML 미리보기."""
        p = Path(path)
        if p.suffix.lower() == ".hwpx":
            return hwpx_service.render_html(p)

        text = await self.get_text(path)
        escaped = (
            text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
        )
        paragraphs = escaped.split("\n")
        html = "\n".join(
            f"<p>{line}</p>" if line.strip() else "<p>&nbsp;</p>"
            for line in paragraphs
        )
        return (
            '<div style="font-family:\'Noto Sans KR\',sans-serif;'
            'font-size:13px;line-height:1.8;padding:20px;">'
            f"{html}</div>"
        )

    async def create_document(
        self, template: str, fields: dict, output_path: str | None = None
    ) -> dict:
        """새 HWPX 생성."""
        if not output_path:
            output_path = str(
                Path(settings.WORKING_DIR) / f"{fields.get('제목', 'document')}.hwpx"
            )
        result = hwpx_service.create_from_template(
            template_name=template,
            fields=fields,
            output_path=output_path,
        )
        await self._index_file(result)
        log.info("문서 생성", action="create_hwpx", path=str(result))
        return {"path": str(result), "success": True}

    async def edit_document(
        self, path: str, operation: str, text: str, search: str | None = None
    ) -> dict:
        """문서 편집."""
        p = Path(path)
        if not p.exists():
            return {"error": "파일을 찾을 수 없습니다"}
        if p.suffix.lower() != ".hwpx":
            return {"error": "HWPX 파일만 편집 가능합니다"}

        if operation == "append":
            hwpx_service.append_text(p, text)
        elif operation == "replace" and search:
            hwpx_service.replace_text(p, search, text)
        else:
            return {"error": f"알 수 없는 작업: {operation}"}

        await self._index_file(p)
        return {"path": str(p), "success": True}

    async def delete_document(self, path: str) -> dict:
        """소프트 삭제 (DB에서 제거, 파일은 유지)."""
        async with get_db() as db:
            await db.execute("DELETE FROM documents WHERE path = ?", (path,))
            await db.execute(
                "DELETE FROM documents_fts WHERE path = ?", (path,)
            )
        return {"path": path, "deleted": True}

    async def _index_file(self, path: Path) -> None:
        """파일을 DB에 인덱싱."""
        try:
            text = hwpx_service.read_text(path) if path.suffix == ".hwpx" else ""
            text_hash = hashlib.sha256(text.encode()).hexdigest()

            async with get_db() as db:
                await db.execute(
                    "INSERT OR REPLACE INTO documents "
                    "(path, filename, ext, size_bytes, text_hash) "
                    "VALUES (?, ?, ?, ?, ?)",
                    (
                        str(path),
                        path.name,
                        path.suffix.lstrip("."),
                        path.stat().st_size,
                        text_hash,
                    ),
                )

                if text:
                    await db.execute(
                        "INSERT OR REPLACE INTO documents_fts "
                        "(path, filename, content) VALUES (?, ?, ?)",
                        (str(path), path.name, text),
                    )
        except Exception as e:
            log.warning("인덱싱 실패", path=str(path), error=str(e))

    @staticmethod
    def _extract_pdf_text(path: Path) -> str:
        try:
            import fitz  # PyMuPDF

            doc = fitz.open(str(path))
            return "\n".join(page.get_text() for page in doc)
        except ImportError:
            return "[PyMuPDF 미설치 — pip install PyMuPDF]"

    @staticmethod
    def _extract_docx_text(path: Path) -> str:
        try:
            from docx import Document

            doc = Document(str(path))
            return "\n".join(p.text for p in doc.paragraphs)
        except ImportError:
            return "[python-docx 미설치]"


document_service = DocumentService()
