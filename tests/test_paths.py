"""backend/paths.py 테스트."""

from pathlib import Path

from backend import paths


def test_is_frozen_returns_false_in_dev():
    assert paths.is_frozen() is False


def test_bundle_dir_is_project_root():
    bd = paths.bundle_dir()
    assert bd.is_dir()
    assert (bd / "pyproject.toml").exists()


def test_app_data_dir_created():
    d = paths.app_data_dir()
    assert d.is_dir()


def test_migrations_dir_exists():
    d = paths.migrations_dir()
    assert d.is_dir()
    sql_files = list(d.glob("*.sql"))
    assert len(sql_files) >= 2  # 001, 002


def test_bundled_examples_dir_exists():
    d = paths.bundled_examples_dir()
    assert d.is_dir()
    json_files = list(d.glob("*.json"))
    assert len(json_files) >= 1


def test_workspace_dir_created():
    d = paths.workspace_dir()
    assert d.is_dir()


def test_exports_dir_created():
    d = paths.exports_dir()
    assert d.is_dir()


def test_imports_dir_created():
    d = paths.imports_dir()
    assert d.is_dir()


def test_optimized_pipelines_dir_created():
    d = paths.optimized_pipelines_dir()
    assert d.is_dir()


def test_db_path_parent_exists():
    p = paths.db_path()
    assert p.parent.is_dir()
    assert p.name == "gm_ai_hub.db"


def test_env_file_path():
    p = paths.env_file_path()
    assert p.name == ".env"
    assert "GM-AI-Hub" in str(p)
