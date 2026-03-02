"""Centralized path resolution for frozen (PyInstaller) and development modes.

Bundle paths (read-only)  — migrations SQL, examples JSON, frontend dist
User data paths (writable) — database, workspace, exports, optimized pipelines
"""

from __future__ import annotations

import os
import sys
from pathlib import Path


def is_frozen() -> bool:
    """True when running inside a PyInstaller bundle."""
    return getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS")


def bundle_dir() -> Path:
    """Root of bundled read-only files.

    Frozen: sys._MEIPASS (temp extraction dir)
    Dev:    project root (where pyproject.toml lives)
    """
    if is_frozen():
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parent.parent


def app_data_dir() -> Path:
    """User-writable application data directory.

    Windows: %LOCALAPPDATA%/GM-AI-Hub
    Other:   ~/.gm-ai-hub
    """
    local = os.environ.get("LOCALAPPDATA")
    if local:
        d = Path(local) / "GM-AI-Hub"
    else:
        d = Path.home() / ".gm-ai-hub"
    d.mkdir(parents=True, exist_ok=True)
    return d


# ── Bundle paths (read-only) ─────────────────────────────────────


def migrations_dir() -> Path:
    return bundle_dir() / "backend" / "db" / "migrations"


def frontend_dist() -> Path:
    return bundle_dir() / "frontend" / "dist"


def bundled_examples_dir() -> Path:
    return bundle_dir() / "data" / "examples"


def bundled_templates_dir() -> Path:
    return bundle_dir() / "data" / "templates"


# ── User data paths (read-write) ─────────────────────────────────


def workspace_dir() -> Path:
    d = app_data_dir() / "workspace"
    d.mkdir(parents=True, exist_ok=True)
    return d


def db_path() -> Path:
    return app_data_dir() / "gm_ai_hub.db"


def exports_dir() -> Path:
    d = app_data_dir() / "workspace" / "exports"
    d.mkdir(parents=True, exist_ok=True)
    return d


def imports_dir() -> Path:
    d = app_data_dir() / "workspace" / "imports"
    d.mkdir(parents=True, exist_ok=True)
    return d


def optimized_pipelines_dir() -> Path:
    d = app_data_dir() / "optimized"
    d.mkdir(parents=True, exist_ok=True)
    return d


def user_examples_dir() -> Path:
    d = app_data_dir() / "examples"
    d.mkdir(parents=True, exist_ok=True)
    return d


def user_samples_dir() -> Path:
    d = app_data_dir() / "samples"
    d.mkdir(parents=True, exist_ok=True)
    return d


def env_file_path() -> Path:
    return app_data_dir() / ".env"


def chat_images_dir() -> Path:
    d = app_data_dir() / "chat_images"
    d.mkdir(parents=True, exist_ok=True)
    return d


def log_dir() -> Path:
    d = app_data_dir() / "logs"
    d.mkdir(parents=True, exist_ok=True)
    return d
