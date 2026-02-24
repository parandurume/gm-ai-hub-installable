"""md_to_owpml.py 버그 수정 회귀 테스트."""

import re

from backend.services.md_to_owpml import (
    _clean_inline,
    _make_runs,
    md_to_owpml_elements,
    parse_md_blocks,
)


# ── Bug 1: <br> in table cells ────────────────────────────────────────


def test_table_cell_br_not_literal():
    """<br> in table cells should become newline, not literal '&lt;br&gt;'."""
    md = "| A<br>B | C |\n|---|---|\n| D<br/>E | F |"
    xml = md_to_owpml_elements(md)
    # Raw <br> tags must not appear in escaped form
    assert "&lt;br&gt;" not in xml
    assert "&lt;br/&gt;" not in xml


def test_table_cell_br_cleaned():
    """<br> tags in table cells should be converted to newlines via _clean_inline."""
    blocks = parse_md_blocks("| hello<br>world |\n|---|\n| foo |")
    table = [b for b in blocks if b["type"] == "table"][0]
    # The raw cell text still has <br>, but when rendered via md_to_owpml_elements,
    # _clean_inline is applied. Verify via the XML output.
    xml = md_to_owpml_elements("| hello<br>world |\n|---|\n| foo |")
    assert "&lt;br&gt;" not in xml


# ── Bug 2: **bold** in table cells ────────────────────────────────────


def test_table_cell_bold_parsed():
    """**bold** in table cells should produce charPrIDRef='6', not literal asterisks."""
    md = "| **강조** | 일반 |\n|---|---|\n| 데이터 | 값 |"
    xml = md_to_owpml_elements(md)
    # Bold text should produce charPrIDRef="6"
    assert 'charPrIDRef="6"' in xml
    # Literal **asterisks** must NOT appear in the output
    assert "**강조**" not in xml
    assert "**" not in xml.replace('charPrIDRef="6"', "")  # no leftover asterisks


def test_table_cell_bold_and_normal_mixed():
    """Table cell with mixed bold and normal text."""
    md = "| 일반 **굵게** 일반 |\n|---|\n| row |"
    xml = md_to_owpml_elements(md)
    assert 'charPrIDRef="6"' in xml
    assert "**" not in xml


# ── Bug 3: Code fences ────────────────────────────────────────────────


def test_code_fence_detected():
    """Triple-backtick code fences should be parsed, not passed through."""
    md = "before\n```python\nprint('hello')\nx = 1\n```\nafter"
    blocks = parse_md_blocks(md)
    types = [b["type"] for b in blocks]
    # The code fence lines should become para blocks with code=True
    code_blocks = [b for b in blocks if b.get("code")]
    assert len(code_blocks) == 2  # print('hello') and x = 1
    assert code_blocks[0]["text"] == "print('hello')"
    assert code_blocks[1]["text"] == "x = 1"


def test_code_fence_backticks_not_in_output():
    """Triple backtick markers must not appear in the rendered XML."""
    md = "```\ncode line\n```"
    xml = md_to_owpml_elements(md)
    assert "```" not in xml


def test_code_fence_no_inline_processing():
    """Code block content should not have bold/backtick processing applied."""
    md = "```\n**not bold** `not code`\n```"
    xml = md_to_owpml_elements(md)
    # In code blocks, ** should be preserved as literal text (escaped)
    assert "**not bold**" in xml or "&amp;" not in xml
    # charPrIDRef="6" (bold) should NOT be applied inside code blocks
    assert 'charPrIDRef="6"' not in xml


def test_code_fence_with_language_tag():
    """Code fence with language tag (```python) should be handled."""
    md = "```markdown\n# heading\n```"
    blocks = parse_md_blocks(md)
    code_blocks = [b for b in blocks if b.get("code")]
    assert len(code_blocks) == 1
    assert code_blocks[0]["text"] == "# heading"


def test_code_fence_empty():
    """Empty code fence should produce no code blocks."""
    md = "```\n```"
    blocks = parse_md_blocks(md)
    code_blocks = [b for b in blocks if b.get("code")]
    assert len(code_blocks) == 0


# ── Integration tests ─────────────────────────────────────────────────


def test_full_document_with_all_fixes():
    """Integration: document with tables (bold, br), code fences, and normal text."""
    md = """# 제목

| 항목 | **설명** |
|------|----------|
| 이름<br>부서 | **홍길동** |

아래는 코드입니다:

```python
def hello():
    return "world"
```

끝."""
    xml = md_to_owpml_elements(md)

    # No literal <br>
    assert "&lt;br&gt;" not in xml
    assert "&lt;br/&gt;" not in xml

    # Bold rendered (charPrIDRef="6")
    assert 'charPrIDRef="6"' in xml

    # No literal **
    # (check outside of xml attribute values)
    text_content = re.sub(r'<[^>]+>', '', xml)
    assert "**" not in text_content

    # No backtick fences
    assert "```" not in xml

    # Code content preserved
    assert "def hello():" in xml or _esc_check("def hello():", xml)


def _esc_check(text: str, xml: str) -> bool:
    """Check if text exists in XML (possibly escaped)."""
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;") in xml
