"""web_fetch_service 단위 테스트."""

from __future__ import annotations

import pytest

from backend.services.web_fetch_service import (
    build_augmented_instruction,
    extract_urls,
    _strip_html,
)


class TestExtractUrls:
    """URL 추출 테스트."""

    def test_single_url(self):
        text = "참고: https://example.com/page 내용을 바탕으로 작성"
        assert extract_urls(text) == ["https://example.com/page"]

    def test_multiple_urls(self):
        text = "https://a.com 과 https://b.com 참고"
        assert extract_urls(text) == ["https://a.com", "https://b.com"]

    def test_max_3_urls(self):
        text = " ".join(f"https://site{i}.com" for i in range(5))
        assert len(extract_urls(text)) == 3

    def test_no_urls(self):
        text = "URL 없이 일반 텍스트만 있음"
        assert extract_urls(text) == []

    def test_dedup(self):
        text = "https://example.com 이것을 보세요 https://example.com"
        assert extract_urls(text) == ["https://example.com"]

    def test_trailing_punctuation_stripped(self):
        text = "링크: https://example.com/page. 다음은"
        urls = extract_urls(text)
        assert urls == ["https://example.com/page"]

    def test_http_scheme(self):
        text = "http://legacy-site.go.kr/doc"
        assert extract_urls(text) == ["http://legacy-site.go.kr/doc"]

    def test_url_with_query_params(self):
        text = "https://example.com/search?q=test&page=1 참고"
        urls = extract_urls(text)
        assert urls[0] == "https://example.com/search?q=test&page=1"


class TestStripHtml:
    """HTML 태그 제거 테스트."""

    def test_basic_tags(self):
        html = "<html><body><p>Hello World</p></body></html>"
        title, text = _strip_html(html)
        assert "Hello World" in text
        assert title == ""

    def test_title_extraction(self):
        html = "<html><head><title>Test Page</title></head><body>Content</body></html>"
        title, text = _strip_html(html)
        assert title == "Test Page"

    def test_script_removal(self):
        html = "<body><script>var x=1;</script><p>Visible</p></body>"
        _, text = _strip_html(html)
        assert "var x=1" not in text
        assert "Visible" in text

    def test_style_removal(self):
        html = "<body><style>.x{color:red}</style><p>Visible</p></body>"
        _, text = _strip_html(html)
        assert "color:red" not in text
        assert "Visible" in text

    def test_entity_decoding(self):
        html = "<p>A &amp; B &lt; C</p>"
        _, text = _strip_html(html)
        assert "A & B < C" in text


class TestBuildAugmentedInstruction:
    """지시사항 보강 테스트."""

    def test_no_pages(self):
        result = build_augmented_instruction("기안문 작성", [])
        assert result == "기안문 작성"

    def test_with_success_page(self):
        pages = [{"url": "https://example.com", "title": "Example", "text": "Page content", "error": None}]
        result = build_augmented_instruction("기안문 작성", pages)
        assert "기안문 작성" in result
        assert "[참고 웹 페이지 내용]" in result
        assert "Page content" in result
        assert "example.com" in result

    def test_with_error_page(self):
        pages = [{"url": "https://fail.com", "title": "", "text": "", "error": "시간 초과"}]
        result = build_augmented_instruction("기안문 작성", pages)
        assert "실패: 시간 초과" in result

    def test_mixed_pages(self):
        pages = [
            {"url": "https://ok.com", "title": "OK", "text": "Good content", "error": None},
            {"url": "https://fail.com", "title": "", "text": "", "error": "HTTP 404"},
        ]
        result = build_augmented_instruction("기안문 작성", pages)
        assert "Good content" in result
        assert "HTTP 404" in result
