"""문서 관리 API — /api/documents."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import HTMLResponse

from backend.models.document import DocumentCreateRequest, DocumentEditRequest
from backend.services.document_service import document_service
from backend.services.pii_service import pii_service

router = APIRouter(prefix="/api/documents", tags=["documents"])


@router.get("")
async def list_documents(
    folder: str | None = None,
    ext: str | None = None,
    recursive: bool = True,
):
    """파일 목록."""
    files = await document_service.list_documents(folder, ext, recursive)
    return {"files": files}


# ── Query-parameter endpoints (robust for Windows paths) ────────────

@router.get("/meta")
async def get_metadata_by_query(path: str = Query(...)):
    """파일 메타데이터 (query param)."""
    meta = await document_service.get_metadata(path)
    if "error" in meta:
        raise HTTPException(status_code=404, detail=meta["error"])
    return meta


@router.get("/preview")
async def get_preview_by_query(path: str = Query(...)):
    """HTML 미리보기 (query param)."""
    try:
        html = await document_service.get_preview(path)
        return HTMLResponse(content=html)
    except FileNotFoundError:
        error_html = (
            '<div style="padding:20px;color:#c0392b;font-size:13px;">'
            f'파일을 찾을 수 없습니다: {path}</div>'
        )
        return HTMLResponse(content=error_html, status_code=200)
    except Exception as e:
        error_html = (
            '<div style="padding:20px;color:#c0392b;font-size:13px;">'
            f'미리보기 실패: {type(e).__name__}</div>'
        )
        return HTMLResponse(content=error_html, status_code=200)


@router.get("/text-content")
async def get_text_by_query(path: str = Query(...)):
    """텍스트 추출 (query param)."""
    text = await document_service.get_text(path)
    return {"path": path, "text": text}


# ── Path-parameter endpoints (legacy) ───────────────────────────────

@router.get("/{path:path}/text")
async def get_text(path: str):
    """텍스트 추출."""
    text = await document_service.get_text(path)
    return {"path": path, "text": text}


@router.get("/{path:path}/preview")
async def get_preview(path: str):
    """HTML 미리보기."""
    try:
        html = await document_service.get_preview(path)
        return HTMLResponse(content=html)
    except Exception as e:
        error_html = (
            '<div style="padding:20px;color:#c0392b;font-size:13px;">'
            f'미리보기 실패: {type(e).__name__}</div>'
        )
        return HTMLResponse(content=error_html, status_code=200)


@router.get("/{path:path}")
async def get_metadata(path: str):
    """파일 메타데이터."""
    meta = await document_service.get_metadata(path)
    if "error" in meta:
        raise HTTPException(status_code=404, detail=meta["error"])
    return meta


@router.post("")
async def create_document(req: DocumentCreateRequest):
    """새 HWPX 생성."""
    result = await document_service.create_document(
        template=req.template, fields=req.fields, output_path=req.output_path
    )
    return result


@router.put("/{path:path}")
async def edit_document(path: str, req: DocumentEditRequest):
    """기존 문서 편집."""
    result = await document_service.edit_document(
        path=path,
        operation=req.operation,
        text=req.text,
        search=req.search,
    )
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.delete("/{path:path}")
async def delete_document(path: str):
    """삭제 (소프트)."""
    return await document_service.delete_document(path)


@router.post("/{path:path}/export")
async def export_document(path: str, destination: str):
    """USB 내보내기 (PII 게이트)."""
    import shutil
    from pathlib import Path

    # PII 게이트
    scan = await pii_service.scan_file(path)
    if not scan.get("passed", True):
        return {
            "blocked": True,
            "reason": f"PII 발견: {list(scan.get('found', {}).keys())}",
            "pii_count": scan.get("total_found", 0),
            "require_confirmation": True,
        }

    dest = Path(destination) / Path(path).name
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(path, dest)
    return {"success": True, "destination": str(dest)}


@router.post("/index/prune")
async def prune_index():
    """삭제된 파일의 스테일 인덱스 항목 제거."""
    from backend.services.index_service import index_service

    removed = await index_service.prune_stale()
    return {"pruned": removed}


@router.post("/index/rebuild")
async def rebuild_index():
    """인덱스 재구축 (스테일 정리 포함)."""
    from backend.services.index_service import index_service

    return await index_service.rebuild_index()
