"""파일시스템 탐색 API — /api/filesystem."""

from __future__ import annotations

import os
import string
from pathlib import Path

from fastapi import APIRouter, Query

router = APIRouter(prefix="/api/filesystem", tags=["filesystem"])


def _safe_path(path_str: str) -> Path:
    """Resolve and validate path (prevent traversal attacks)."""
    p = Path(path_str).resolve()
    return p


@router.get("/browse")
async def browse_directory(path: str = Query(default="")):
    """디렉토리 내용 목록 반환. path가 비어있으면 드라이브 루트 목록(Windows) 또는 / 반환."""
    # Empty path → list drives on Windows, root on Unix
    if not path:
        if os.name == "nt":
            drives = []
            for letter in string.ascii_uppercase:
                drive = f"{letter}:\\"
                if os.path.isdir(drive):
                    drives.append({
                        "name": f"{letter}:",
                        "path": drive,
                        "is_dir": True,
                    })
            return {"path": "", "parent": None, "items": drives}
        else:
            path = "/"

    target = _safe_path(path)

    if not target.exists():
        return {"path": str(target), "parent": str(target.parent), "items": [], "error": "경로가 존재하지 않습니다"}

    if not target.is_dir():
        return {"path": str(target), "parent": str(target.parent), "items": [], "error": "디렉토리가 아닙니다"}

    items = []
    try:
        for entry in sorted(target.iterdir(), key=lambda e: (not e.is_dir(), e.name.lower())):
            # Skip hidden files/folders and system files
            if entry.name.startswith(".") or entry.name.startswith("$"):
                continue
            try:
                items.append({
                    "name": entry.name,
                    "path": str(entry),
                    "is_dir": entry.is_dir(),
                })
            except PermissionError:
                continue
    except PermissionError:
        return {"path": str(target), "parent": str(target.parent), "items": [], "error": "접근 권한이 없습니다"}

    parent = str(target.parent) if target.parent != target else None

    return {"path": str(target), "parent": parent, "items": items}
