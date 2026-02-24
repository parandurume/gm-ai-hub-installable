"""GM-AI-Hub 설정 — 환경변수 기반 Pydantic Settings."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings


def _detect_hwp_tier() -> str:
    """Runtime HWP read capability."""
    try:
        import hwp5  # noqa: F401
        return "pyhwp"
    except ImportError:
        return "none"


def _detect_environment() -> str:
    """Detect runtime environment: govpc, laptop, or laptop_high_ram."""
    import os
    if os.getenv("GOVPC_MODE", "false").lower() == "true":
        return "govpc"
    try:
        import psutil
        ram_gb = psutil.virtual_memory().total / (1024**3)
        return "laptop_high_ram" if ram_gb >= 48 else "laptop"
    except ImportError:
        return "laptop"


class Settings(BaseSettings):
    """All config loaded from .env or environment variables."""

    # ── Server ──
    APP_HOST: str = "127.0.0.1"
    APP_PORT: int = 8080
    APP_DEBUG: bool = False
    APP_ENV: Literal["development", "production"] = "production"

    # ── Filesystem (project-relative by default) ──
    WORKING_DIR: Path = Path("./data/workspace")
    EXPORT_DIR: Path = Path("./data/workspace/exports")
    IMPORT_DIR: Path = Path("./data/workspace/imports")

    # ── Ollama ──
    OLLAMA_BASE_URL: str = "http://127.0.0.1:11434"
    OLLAMA_MODEL: str = "gpt-oss:20b"
    OLLAMA_EMBED_MODEL: str = "nomic-embed-text"
    OLLAMA_TIMEOUT: int = 120

    # ── Database ──
    DB_PATH: Path = Path("./data/workspace/gm_ai_hub.db")

    # ── Security ──
    PII_SCAN_ON_EXPORT: bool = True
    AUDIT_LOG: bool = True
    LOG_CONTENT: bool = False

    # ── Folder watch ──
    WATCH_PATHS: str = ""

    # ── MCP ──
    MCP_PORT: int = 8081
    MCP_TRANSPORT: Literal["stdio", "sse"] = "stdio"

    # ── Government PC ──
    GOVPC_MODE: bool = False
    GOVPC_BIND_IP: str = "192.168.100.1"
    ALLOWED_CLIENT_IPS: str = "192.168.100.2"

    # ── Department info (auto-fill) ──
    DEPARTMENT_NAME: str = ""
    DEPARTMENT_CODE: str = ""
    OFFICER_NAME: str = ""

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

    @property
    def watch_paths_list(self) -> list[str]:
        if not self.WATCH_PATHS:
            return []
        return [p.strip() for p in self.WATCH_PATHS.split(",") if p.strip()]

    @property
    def environment(self) -> str:
        return _detect_environment()

    @property
    def hwp_tier(self) -> str:
        return _detect_hwp_tier()

    def ensure_directories(self) -> None:
        """Resolve relative paths and create directories."""
        self.WORKING_DIR = self.WORKING_DIR.resolve()
        self.EXPORT_DIR = self.EXPORT_DIR.resolve()
        self.IMPORT_DIR = self.IMPORT_DIR.resolve()
        self.DB_PATH = self.DB_PATH.resolve()

        self.WORKING_DIR.mkdir(parents=True, exist_ok=True)
        self.EXPORT_DIR.mkdir(parents=True, exist_ok=True)
        self.IMPORT_DIR.mkdir(parents=True, exist_ok=True)
        self.DB_PATH.parent.mkdir(parents=True, exist_ok=True)


settings = Settings()
