"""md_to_owpml 변환기 단위 테스트."""

from __future__ import annotations

import pytest

from backend.services.md_to_owpml import (
    _clean_inline,
    _make_runs,
    _make_table,
    md_to_owpml_elements,
    parse_md_blocks,
)


class TestParseBlocks:
    """마크다운 블록 파싱 테스트."""

    def test_heading(self):
        blocks = parse_md_blocks("## 제목")
        assert blocks[0]["type"] == "para"
        assert blocks[0]["style"] == 2
        assert blocks[0]["text"] == "제목"

    def test_table(self):
        md = "| A | B |\n|---|---|\n| 1 | 2 |"
        blocks = parse_md_blocks(md)
        tbl = [b for b in blocks if b["type"] == "table"]
        assert len(tbl) == 1
        assert tbl[0]["has_header"] is True
        assert len(tbl[0]["rows"]) == 2  # header + 1 data row (separator excluded)

    def test_table_no_header(self):
        md = "| A | B |\n| 1 | 2 |"
        blocks = parse_md_blocks(md)
        tbl = [b for b in blocks if b["type"] == "table"]
        assert tbl[0]["has_header"] is False

    def test_ordered_list(self):
        blocks = parse_md_blocks("1. 첫째\n2. 둘째")
        assert blocks[0]["type"] == "list_item"
        assert blocks[0]["ordered"] is True
        assert blocks[0]["number"] == 1

    def test_unordered_list(self):
        blocks = parse_md_blocks("- 항목A\n- 항목B")
        assert blocks[0]["type"] == "list_item"
        assert blocks[0]["ordered"] is False

    def test_blockquote(self):
        blocks = parse_md_blocks("> 인용문")
        assert blocks[0]["type"] == "blockquote"
        assert blocks[0]["text"] == "인용문"

    def test_horizontal_rule(self):
        blocks = parse_md_blocks("---")
        assert blocks[0]["type"] == "hr"

    def test_empty_line(self):
        blocks = parse_md_blocks("\n\n")
        assert any(b["type"] == "empty" for b in blocks)

    def test_plain_text(self):
        blocks = parse_md_blocks("일반 텍스트입니다.")
        assert blocks[0]["type"] == "para"
        assert blocks[0]["style"] == 0


class TestCleanInline:
    """인라인 정리 테스트."""

    def test_br_removal(self):
        assert _clean_inline("A<br>B") == "A\nB"
        assert _clean_inline("A<br/>B") == "A\nB"

    def test_backtick_removal(self):
        assert _clean_inline("`code`") == "code"

    def test_whitespace_trim(self):
        assert _clean_inline("  text  ") == "text"


class TestMakeRuns:
    """Bold 인라인 처리 테스트."""

    def test_plain_text(self):
        xml = _make_runs("일반 텍스트")
        assert 'charPrIDRef="0"' in xml
        assert "일반 텍스트" in xml

    def test_bold_text(self):
        xml = _make_runs("**굵은 텍스트**")
        assert 'charPrIDRef="6"' in xml
        assert "굵은 텍스트" in xml

    def test_mixed_bold(self):
        xml = _make_runs("앞 **굵게** 뒤")
        assert xml.count("<hp:run") == 3
        assert 'charPrIDRef="6"' in xml
        assert 'charPrIDRef="0"' in xml


class TestMakeTable:
    """OWPML 테이블 생성 테스트."""

    def test_basic_table(self):
        rows = [["제목", "값"], ["A", "1"]]
        xml = _make_table(rows, has_header=True, tbl_id="100", para_id=1)
        assert "<hp:tbl" in xml
        assert 'rowCnt="2"' in xml
        assert 'colCnt="2"' in xml
        assert "제목" in xml
        assert "A" in xml

    def test_header_bold(self):
        rows = [["H1", "H2"], ["D1", "D2"]]
        xml = _make_table(rows, has_header=True, tbl_id="101", para_id=1)
        # Header cells use bold charPr (id=6)
        assert 'charPrIDRef="6"' in xml
        # Data cells use normal charPr (id=0)
        assert 'charPrIDRef="0"' in xml

    def test_cell_addr(self):
        rows = [["A", "B"], ["C", "D"]]
        xml = _make_table(rows, has_header=True, tbl_id="102", para_id=1)
        assert 'colAddr="0" rowAddr="0"' in xml
        assert 'colAddr="1" rowAddr="0"' in xml
        assert 'colAddr="0" rowAddr="1"' in xml
        assert 'colAddr="1" rowAddr="1"' in xml

    def test_empty_rows(self):
        xml = _make_table([], has_header=False, tbl_id="103", para_id=1)
        assert xml == ""

    def test_table_in_elements(self):
        xml = md_to_owpml_elements(
            "| H1 | H2 |\n|---|---|\n| D1 | D2 |"
        )
        assert "<hp:tbl" in xml
        assert 'charPrIDRef="6"' in xml


class TestMdToOwpmlElements:
    """전체 변환 통합 테스트."""

    def test_simple_text(self):
        xml = md_to_owpml_elements("안녕하세요")
        assert "<hp:p" in xml
        assert "안녕하세요" in xml

    def test_heading_conversion(self):
        xml = md_to_owpml_elements("## 제목1\n\n본문")
        assert 'styleIDRef="2"' in xml

    def test_table_conversion(self):
        md = "| 구분 | 내용 |\n|---|---|\n| A | B |"
        xml = md_to_owpml_elements(md)
        assert "<hp:tbl" in xml
        assert "구분" in xml
        assert "내용" in xml
        assert "A" in xml

    def test_bold_in_text(self):
        xml = md_to_owpml_elements("이것은 **중요** 합니다")
        assert 'charPrIDRef="6"' in xml
        assert "중요" in xml

    def test_table_has_proper_structure(self):
        """테이블이 올바른 OWPML hp:tbl 구조로 변환되어야 한다."""
        md = "| A | B |\n|---|---|\n| 1 | 2 |"
        xml = md_to_owpml_elements(md)
        assert "<hp:tbl" in xml
        assert "<hp:tr>" in xml
        assert "<hp:tc" in xml
        assert "<hp:subList" in xml
        assert "<hp:cellAddr" in xml
        assert "<hp:cellSpan" in xml
        assert "<hp:cellSz" in xml

    def test_mixed_content(self):
        md = "## 개요\n\n내용입니다.\n\n| 항목 | 값 |\n|---|---|\n| A | 1 |\n\n---\n\n끝."
        xml = md_to_owpml_elements(md)
        assert 'styleIDRef="2"' in xml  # heading
        assert "항목" in xml  # table content
        assert "끝." in xml  # trailing text

    def test_xml_escaping(self):
        xml = md_to_owpml_elements("A & B < C")
        assert "&amp;" in xml
        assert "&lt;" in xml
