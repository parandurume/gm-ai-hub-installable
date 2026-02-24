"""HWPX 서비스 단위 테스트."""

import tempfile
from pathlib import Path

import pytest

from backend.services.hwpx_service import HwpxService


@pytest.fixture
def svc():
    return HwpxService()


@pytest.fixture
def tmp_dir():
    with tempfile.TemporaryDirectory(prefix="hwpx_test_") as d:
        yield Path(d)


class TestHwpxCreate:
    def test_create_produces_valid_hwpx(self, svc, tmp_dir):
        path = tmp_dir / "test.hwpx"
        result = svc.create(path, "# 테스트 문서\n\n본문 내용입니다.")
        assert result.exists()
        assert result.suffix == ".hwpx"

        # 유효성 검사
        validation = svc.validate_hwpx(result)
        assert validation["valid"] is True

    def test_create_and_read(self, svc, tmp_dir):
        path = tmp_dir / "roundtrip.hwpx"
        svc.create(path, "테스트 본문")
        text = svc.read_text(path)
        assert "테스트 본문" in text

    def test_create_with_heading(self, svc, tmp_dir):
        path = tmp_dir / "heading.hwpx"
        svc.create(path, "# 제목\n## 부제목\n본문")
        text = svc.read_text(path)
        assert "제목" in text
        assert "본문" in text


class TestHwpxRead:
    def test_read_text_from_created(self, svc, tmp_dir):
        path = tmp_dir / "read.hwpx"
        svc.create(path, "안녕하세요")
        text = svc.read_text(path)
        assert "안녕하세요" in text

    def test_read_metadata(self, svc, tmp_dir):
        path = tmp_dir / "meta.hwpx"
        svc.create(path, "메타 테스트")
        meta = svc.read_metadata(path)
        assert meta["format"] == "hwpx"
        assert meta["filename"] == "meta.hwpx"


class TestHwpxHtml:
    def test_render_html(self, svc, tmp_dir):
        path = tmp_dir / "preview.hwpx"
        svc.create(path, "미리보기 테스트")
        html = svc.render_html(path)
        assert "<div" in html
        assert "미리보기 테스트" in html


class TestHwpxEdit:
    def test_append_text(self, svc, tmp_dir):
        path = tmp_dir / "append.hwpx"
        svc.create(path, "원본 텍스트")
        svc.append_text(path, "추가된 텍스트")
        text = svc.read_text(path)
        assert "원본 텍스트" in text
        assert "추가된 텍스트" in text

    def test_replace_text(self, svc, tmp_dir):
        path = tmp_dir / "replace.hwpx"
        svc.create(path, "교체할 단어 포함")
        svc.replace_text(path, "교체할 단어", "새로운 단어")
        text = svc.read_text(path)
        assert "새로운 단어" in text
        assert "교체할 단어" not in text


class TestHwpxValidation:
    def test_validate_valid_file(self, svc, tmp_dir):
        path = tmp_dir / "valid.hwpx"
        svc.create(path, "유효한 파일")
        result = svc.validate_hwpx(path)
        assert result["valid"] is True

    def test_validate_invalid_file(self, svc, tmp_dir):
        path = tmp_dir / "invalid.hwpx"
        path.write_text("not a zip")
        result = svc.validate_hwpx(path)
        assert result["valid"] is False
