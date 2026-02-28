# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec — GM-AI-Hub Desktop (one-folder mode).

두 개의 실행 파일을 생성:
  1. GM-AI-Hub.exe — 시스템 트레이 런처 (windowed, 콘솔 없음)
  2. gm-hub-server.exe — FastAPI 서버 (console, 런처가 숨겨서 실행)
"""

import os
from pathlib import Path

block_cipher = None

# ── STT: ctranslate2 + PyAV 네이티브 라이브러리 수집 ───────────────
# faster-whisper → ctranslate2 (C++ DLL),  av → PyAV (ffmpeg DLL)
# PyInstaller 정적 분석으로 감지되지 않으므로 명시적으로 포함
from PyInstaller.utils.hooks import collect_dynamic_libs, collect_data_files  # noqa: E402

_extra_binaries = []
_extra_datas = []

try:
    _extra_binaries += collect_dynamic_libs("ctranslate2")
except Exception:
    pass

try:
    _extra_datas += collect_data_files("ctranslate2")
except Exception:
    pass

try:
    _extra_binaries += collect_dynamic_libs("av")
except Exception:
    pass

try:
    _extra_datas += collect_data_files("faster_whisper")  # silero_vad_v6.onnx
except Exception:
    pass

PROJECT_ROOT = Path(SPECPATH).parent
BACKEND_DIR = PROJECT_ROOT / "backend"
FRONTEND_DIST = PROJECT_ROOT / "frontend" / "dist"
DATA_DIR = PROJECT_ROOT / "data"
LAUNCHER_DIR = PROJECT_ROOT / "launcher"

# ── 데이터 파일 (번들에 포함) ──────────────────────────────────────
datas = []

# 프론트엔드 빌드 결과
if FRONTEND_DIST.exists():
    datas.append((str(FRONTEND_DIST), "frontend/dist"))

# DB 마이그레이션 SQL
datas.append((str(BACKEND_DIR / "db" / "migrations"), "backend/db/migrations"))

# 데이터 파일 (예시 JSON, 템플릿 등)
if DATA_DIR.exists():
    datas.append((str(DATA_DIR), "data"))

# 런처 아이콘
datas.append((str(LAUNCHER_DIR / "icon.ico"), "launcher"))
datas.append((str(LAUNCHER_DIR / "icon.png"), "launcher"))

# ── 숨겨진 임포트 ──────────────────────────────────────────────────
hidden_imports = [
    # uvicorn 내부
    "uvicorn.logging",
    "uvicorn.loops",
    "uvicorn.loops.auto",
    "uvicorn.loops.asyncio",
    "uvicorn.protocols",
    "uvicorn.protocols.http",
    "uvicorn.protocols.http.auto",
    "uvicorn.protocols.http.h11_impl",
    "uvicorn.protocols.http.httptools_impl",
    "uvicorn.protocols.websockets",
    "uvicorn.protocols.websockets.auto",
    "uvicorn.protocols.websockets.websockets_impl",
    "uvicorn.lifespan",
    "uvicorn.lifespan.on",
    "uvicorn.lifespan.off",
    # FastAPI / Starlette
    "starlette.responses",
    "starlette.routing",
    "starlette.middleware",
    "starlette.middleware.cors",
    "multipart",
    "multipart.multipart",
    # 데이터 관련
    "aiosqlite",
    "sqlite3",
    "pydantic",
    "pydantic_settings",
    # 문서 처리
    "lxml",
    "lxml._elementpath",
    "lxml.etree",
    "openpyxl",
    "docx",
    "pdfplumber",
    # 기타
    "httpx",
    "structlog",
    "watchdog",
    "watchdog.observers",
    "dotenv",
    # Backend 모듈 (동적 임포트 포함)
    "backend",
    "backend.main",
    "backend.paths",
    "backend.config",
    "backend.api",
    "backend.api.router",
    "backend.api.health",
    "backend.api.setup_wizard",
    "backend.api.documents",
    "backend.api.draft",
    "backend.api.search",
    "backend.api.chat",
    "backend.api.meeting",
    "backend.api.complaint",
    "backend.api.regulation",
    "backend.api.pii",
    "backend.api.diff",
    "backend.api.settings_api",
    "backend.api.models",
    "backend.api.optimize",
    "backend.api.filesystem",
    "backend.api.samples",
    "backend.db",
    "backend.db.database",
    "backend.services",
    "backend.services.hwpx_service",
    "backend.services.md_to_owpml",
    "backend.services.web_fetch_service",
    "backend.services.sample_extract_service",
    "backend.models",
    "backend.ai",
    "backend.ai.dspy_config",
    "backend.ai.pipelines",
    "backend.ai.guards",
    "backend.ai.optimization",
    "backend.ai.optimization.auto_dataset",
    "backend.ai.optimization.metrics",
    "backend.ai.optimization.miprov2_runner",
    # STT (faster-whisper) — 함수 내부에서 lazy import되므로 명시 필요
    "backend.services.stt_service",
    "faster_whisper",
    "faster_whisper.audio",
    "faster_whisper.feature_extractor",
    "faster_whisper.tokenizer",
    "faster_whisper.transcribe",
    "faster_whisper.utils",
    "ctranslate2",
    "tokenizers",
    "huggingface_hub",
    "huggingface_hub.utils",
    "av",
]

# ── 제외 모듈 (번들 크기 축소) ──────────────────────────────────────
excludes = [
    "tkinter",
    "matplotlib",
    "scipy",
    # numpy 제외하지 않음 — ctranslate2 / faster-whisper 가 numpy 를 사용함
    "test",
    "unittest",
    "xmlrpc",
    "pdb",
]

# ── 서버 (console) ──────────────────────────────────────────────────
server_a = Analysis(
    [str(PROJECT_ROOT / "backend" / "main.py")],
    pathex=[str(PROJECT_ROOT)],
    binaries=_extra_binaries,
    datas=datas + _extra_datas,
    hiddenimports=hidden_imports,
    hookspath=[str(PROJECT_ROOT / "build" / "hooks")],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

server_pyz = PYZ(server_a.pure, server_a.zipped_data, cipher=block_cipher)

server_exe = EXE(
    server_pyz,
    server_a.scripts,
    [],
    exclude_binaries=True,
    name="gm-hub-server",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    icon=str(LAUNCHER_DIR / "icon.ico"),
)

# ── 트레이 런처 (windowed) ──────────────────────────────────────────
tray_a = Analysis(
    [str(PROJECT_ROOT / "launcher" / "tray.py")],
    pathex=[str(PROJECT_ROOT)],
    binaries=_extra_binaries,
    datas=datas + _extra_datas,
    hiddenimports=hidden_imports + [
        "pystray",
        "pystray._win32",
        "PIL",
        "PIL.Image",
        "PIL.ImageDraw",
        "PIL.ImageFont",
    ],
    hookspath=[str(PROJECT_ROOT / "build" / "hooks")],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

tray_pyz = PYZ(tray_a.pure, tray_a.zipped_data, cipher=block_cipher)

tray_exe = EXE(
    tray_pyz,
    tray_a.scripts,
    [],
    exclude_binaries=True,
    name="GM-AI-Hub",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # windowed — 콘솔 창 없음
    icon=str(LAUNCHER_DIR / "icon.ico"),
)

# ── COLLECT (하나의 폴더에 두 실행 파일 + 공유 라이브러리) ──────────
coll = COLLECT(
    server_exe,
    server_a.binaries,
    server_a.zipfiles,
    server_a.datas,
    tray_exe,
    tray_a.binaries,
    tray_a.zipfiles,
    tray_a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="GM-AI-Hub",
)
