"""마크다운 → OWPML XML 변환기.

AI가 생성한 마크다운 형식의 텍스트를 OWPML(HWPX) XML 요소로 변환한다.
지원:
  - 표(table): ``| col1 | col2 |`` → ``<hp:tbl>``
  - 제목(heading): ``## 제목`` → styled ``<hp:p>``
  - 굵게(bold): ``**텍스트**`` → ``<hp:run>`` with bold charPr
  - 목록(list): ``- 항목`` / ``1. 항목`` → numbered/bulleted paragraphs
  - 인용(blockquote): ``> 텍스트`` → indented paragraph
  - ``<br>`` 태그 → 줄바꿈으로 변환
  - 백틱 코드(backtick): ``code`` → 그냥 텍스트
"""

from __future__ import annotations

import re

# ── 정규식 ─────────────────────────────────────────────────────────────
_BOLD_RE = re.compile(r"\*\*(.+?)\*\*")
_BACKTICK_RE = re.compile(r"`([^`]+)`")
_BR_RE = re.compile(r"<br\s*/?>", re.IGNORECASE)
_TABLE_SEP_RE = re.compile(r"^\|[\s\-:|]+\|$")
_TABLE_ROW_RE = re.compile(r"^\|(.+)\|$")
_ORDERED_RE = re.compile(r"^(\d+)\.\s+(.+)$")
_UNORDERED_RE = re.compile(r"^[-*]\s+(.+)$")
_BLOCKQUOTE_RE = re.compile(r"^>\s*(.*)$")
_HEADING_RE = re.compile(r"^(#{1,5})\s+(.+)$")
_HR_RE = re.compile(r"^-{3,}$")

# OWPML 테이블 너비 기준 (A4 본문 영역 ≈ 42520 HWPUNIT)
_TABLE_WIDTH = 42520
# 테이블 셀 border fill ID (header.xml에 ID=3 추가 필요)
_TBL_BORDER_FILL_ID = "3"
_TBL_HEADER_BORDER_FILL_ID = "4"


def _esc(text: str) -> str:
    """XML 이스케이프."""
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _clean_inline(text: str) -> str:
    """<br>, 백틱 등 인라인 정리 (bold는 유지)."""
    text = _BR_RE.sub("\n", text)
    text = _BACKTICK_RE.sub(r"\1", text)
    return text.strip()


def _make_runs(text: str, base_char_id: int = 0) -> str:
    """인라인 볼드 처리 → <hp:run> 시퀀스 생성.

    ``**bold**`` → charPrIDRef="6" (bold), 나머지 → base_char_id.
    charPr ID 6은 header.xml에 inline-bold용으로 추가한다.
    """
    parts = _BOLD_RE.split(text)
    runs = ""
    for i, part in enumerate(parts):
        if not part:
            continue
        is_bold = i % 2 == 1
        char_id = 6 if is_bold else base_char_id
        runs += (
            f'<hp:run charPrIDRef="{char_id}">'
            f"<hp:t>{_esc(part)}</hp:t>"
            "</hp:run>"
        )
    return runs or f'<hp:run charPrIDRef="{base_char_id}"><hp:t></hp:t></hp:run>'


def _make_para(
    text: str, style_id: int = 0, char_id: int = 0, para_id: int | None = None,
) -> str:
    """일반 텍스트 → <hp:p> 단락."""
    id_attr = f' id="{para_id}"' if para_id is not None else ""
    return (
        f"<hp:p{id_attr}"
        f' paraPrIDRef="{style_id}" styleIDRef="{style_id}"'
        f' pageBreak="0" columnBreak="0" merged="0">'
        f"{_make_runs(_clean_inline(text), char_id)}"
        "</hp:p>"
    )


def _make_table(
    rows: list[list[str]],
    has_header: bool,
    tbl_id: str,
    para_id: int,
) -> str:
    """마크다운 테이블 → OWPML <hp:tbl> XML (hwpxlib 스키마 기반).

    테이블은 <hp:p> > <hp:run> > <hp:tbl> 구조로 단락 안에 삽입된다.
    """
    if not rows:
        return ""

    num_rows = len(rows)
    num_cols = max(len(r) for r in rows)
    col_width = _TABLE_WIDTH // num_cols
    row_height = 2886  # ~1 line height in HWPUNIT

    # 셀 생성
    tr_xml = ""
    for ri, row in enumerate(rows):
        tc_xml = ""
        for ci in range(num_cols):
            val = row[ci].strip() if ci < len(row) else ""
            is_header = has_header and ri == 0
            bf_id = _TBL_HEADER_BORDER_FILL_ID if is_header else _TBL_BORDER_FILL_ID
            char_id = 6 if is_header else 0  # bold for header

            tc_xml += (
                f'<hp:tc name="" header="{1 if is_header else 0}"'
                f' hasMargin="0" protect="0" editable="0"'
                f' dirty="0" borderFillIDRef="{bf_id}">'
                f'<hp:subList id="" textDirection="HORIZONTAL"'
                f' lineWrap="BREAK" vertAlign="CENTER"'
                f' linkListIDRef="0" linkListNextIDRef="0"'
                f' textWidth="0" textHeight="0"'
                f' hasTextRef="0" hasNumRef="0">'
                f'<hp:p id="{para_id}" paraPrIDRef="0" styleIDRef="0"'
                f' pageBreak="0" columnBreak="0" merged="0">'
                f'<hp:run charPrIDRef="{char_id}">'
                f'<hp:t>{_esc(val)}</hp:t>'
                f'</hp:run>'
                f'</hp:p>'
                f'</hp:subList>'
                f'<hp:cellAddr colAddr="{ci}" rowAddr="{ri}"/>'
                f'<hp:cellSpan colSpan="1" rowSpan="1"/>'
                f'<hp:cellSz width="{col_width}" height="{row_height}"/>'
                f'<hp:cellMargin left="510" right="510" top="141" bottom="141"/>'
                f'</hp:tc>'
            )
        tr_xml += f"<hp:tr>{tc_xml}</hp:tr>"

    total_height = num_rows * row_height

    tbl_xml = (
        f'<hp:tbl id="{tbl_id}" zOrder="0"'
        f' numberingType="TABLE" textWrap="TOP_AND_BOTTOM"'
        f' textFlow="BOTH_SIDES" lock="0" dropcapstyle="None"'
        f' pageBreak="CELL" repeatHeader="{1 if has_header else 0}"'
        f' rowCnt="{num_rows}" colCnt="{num_cols}"'
        f' cellSpacing="0" borderFillIDRef="{_TBL_BORDER_FILL_ID}"'
        f' noAdjust="0">'
        f'<hp:sz width="{_TABLE_WIDTH}" widthRelTo="ABSOLUTE"'
        f' height="{total_height}" heightRelTo="ABSOLUTE" protect="0"/>'
        f'<hp:pos treatAsChar="1" affectLSpacing="0"'
        f' flowWithText="1" allowOverlap="0" holdAnchorAndSO="0"'
        f' vertRelTo="PARA" horzRelTo="COLUMN"'
        f' vertAlign="TOP" horzAlign="LEFT"'
        f' vertOffset="0" horzOffset="0"/>'
        f'<hp:outMargin left="283" right="283" top="283" bottom="283"/>'
        f'<hp:inMargin left="510" right="510" top="141" bottom="141"/>'
        f'{tr_xml}'
        f'</hp:tbl>'
    )

    # 테이블을 감싸는 단락
    return (
        f'<hp:p id="{para_id}" paraPrIDRef="0" styleIDRef="0"'
        f' pageBreak="0" columnBreak="0" merged="0">'
        f'<hp:run charPrIDRef="0">'
        f'{tbl_xml}'
        f'</hp:run>'
        f'</hp:p>'
    )


# ── 블록 파서 ──────────────────────────────────────────────────────────

def _parse_table_row(line: str) -> list[str] | None:
    """``| a | b | c |`` → ['a', 'b', 'c'] 또는 None."""
    m = _TABLE_ROW_RE.match(line.strip())
    if not m:
        return None
    return [cell.strip() for cell in m.group(1).split("|")]


def _is_separator_row(line: str) -> bool:
    """``|---|---|`` 형태인지 확인."""
    return bool(_TABLE_SEP_RE.match(line.strip()))


def parse_md_blocks(content: str) -> list[dict]:
    """마크다운 텍스트를 블록 단위로 파싱.

    Returns list of:
      {"type": "para", "text": str, "style": int}
      {"type": "table", "rows": list[list[str]], "has_header": bool}
      {"type": "list_item", "text": str, "ordered": bool, "number": int}
      {"type": "blockquote", "text": str}
      {"type": "hr"}
      {"type": "empty"}
    """
    lines = content.split("\n")
    blocks: list[dict] = []
    i = 0

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        # 빈 줄
        if not stripped:
            blocks.append({"type": "empty"})
            i += 1
            continue

        # 수평선
        if _HR_RE.match(stripped):
            blocks.append({"type": "hr"})
            i += 1
            continue

        # 테이블 감지 — 연속된 | 행들을 모은다
        row = _parse_table_row(stripped)
        if row is not None:
            table_rows: list[list[str]] = []
            has_header = False
            table_rows.append(row)
            i += 1
            while i < len(lines):
                s = lines[i].strip()
                if _is_separator_row(s):
                    has_header = True
                    i += 1
                    continue
                r = _parse_table_row(s)
                if r is not None:
                    table_rows.append(r)
                    i += 1
                else:
                    break
            blocks.append({"type": "table", "rows": table_rows, "has_header": has_header})
            continue

        # 제목
        m = _HEADING_RE.match(stripped)
        if m:
            level = len(m.group(1))
            blocks.append({"type": "para", "text": m.group(2), "style": level})
            i += 1
            continue

        # 인용
        m = _BLOCKQUOTE_RE.match(stripped)
        if m:
            blocks.append({"type": "blockquote", "text": m.group(1)})
            i += 1
            continue

        # 순서형 목록
        m = _ORDERED_RE.match(stripped)
        if m:
            blocks.append({
                "type": "list_item", "text": m.group(2),
                "ordered": True, "number": int(m.group(1)),
            })
            i += 1
            continue

        # 비순서형 목록
        m = _UNORDERED_RE.match(stripped)
        if m:
            blocks.append({
                "type": "list_item", "text": m.group(1),
                "ordered": False, "number": 0,
            })
            i += 1
            continue

        # 일반 텍스트
        blocks.append({"type": "para", "text": stripped, "style": 0})
        i += 1

    return blocks


# ── 메인 변환 ──────────────────────────────────────────────────────────

def md_to_owpml_elements(content: str, start_id: int = 1) -> str:
    """마크다운 텍스트 → OWPML XML 요소 문자열.

    _build_section_xml()에서 sec_pr_para 뒤에 삽입할 XML 문자열을 반환한다.
    start_id: 첫 단락의 id 속성 값 (sec_pr_para가 id=0 사용).
    """
    blocks = parse_md_blocks(content)
    parts: list[str] = []
    pid = start_id
    tbl_inst = 0  # table instance counter

    for block in blocks:
        btype = block["type"]

        if btype == "empty":
            parts.append(
                f'<hp:p id="{pid}" paraPrIDRef="0" styleIDRef="0"'
                ' pageBreak="0" columnBreak="0" merged="0">'
                '<hp:run charPrIDRef="0"><hp:t></hp:t></hp:run>'
                "</hp:p>"
            )
            pid += 1

        elif btype == "hr":
            parts.append(
                f'<hp:p id="{pid}" paraPrIDRef="0" styleIDRef="0"'
                ' pageBreak="0" columnBreak="0" merged="0">'
                '<hp:run charPrIDRef="0"><hp:t></hp:t></hp:run>'
                "</hp:p>"
            )
            pid += 1

        elif btype == "para":
            style = block["style"]
            parts.append(_make_para(block["text"], style, style, para_id=pid))
            pid += 1

        elif btype == "table":
            tbl_inst += 1
            tbl_id = str(1000000 + tbl_inst)
            parts.append(_make_table(
                block["rows"], block["has_header"],
                tbl_id=tbl_id, para_id=pid,
            ))
            pid += 1

        elif btype == "blockquote":
            text = _clean_inline(block["text"])
            parts.append(
                f'<hp:p id="{pid}" paraPrIDRef="0" styleIDRef="0"'
                ' pageBreak="0" columnBreak="0" merged="0">'
                f'<hp:run charPrIDRef="0">'
                f"<hp:t>  {_esc(text)}</hp:t>"
                "</hp:run>"
                "</hp:p>"
            )
            pid += 1

        elif btype == "list_item":
            prefix = f"{block['number']}. " if block["ordered"] else "- "
            text = _clean_inline(block["text"])
            parts.append(
                f'<hp:p id="{pid}" paraPrIDRef="0" styleIDRef="0"'
                ' pageBreak="0" columnBreak="0" merged="0">'
                f"{_make_runs(prefix + text, 0)}"
                "</hp:p>"
            )
            pid += 1

    return "".join(parts)
