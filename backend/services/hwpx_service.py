"""
HWPX 서비스 — ZIP + OWPML XML 기반 읽기/쓰기/미리보기.

OWPML 2011 네임스페이스 사용 (검증된 참조 구현 기반).
mimetype 먼저 기록 (ZIP_STORED), OPC 패키징 준수.
"""

from __future__ import annotations

import shutil
import tempfile
import zipfile
from datetime import date
from io import BytesIO
from pathlib import Path

import structlog
from lxml import etree

from backend.services.md_to_owpml import md_to_owpml_elements

log = structlog.get_logger()

# ── OWPML 2011 네임스페이스 ──────────────────────────────────────────
HP_NS = "http://www.hancom.co.kr/hwpml/2011/paragraph"
HS_NS = "http://www.hancom.co.kr/hwpml/2011/section"
HC_NS = "http://www.hancom.co.kr/hwpml/2011/core"
HH_NS = "http://www.hancom.co.kr/hwpml/2011/head"
HA_NS = "http://www.hancom.co.kr/hwpml/2011/app"
HV_NS = "http://www.hancom.co.kr/hwpml/2011/version"
HPF_NS = "http://www.hancom.co.kr/schema/2011/hpf"
OPF_NS = "http://www.idpf.org/2007/opf/"

HP_NS_ALT = "urn:hancom:hwpml:2011.paragraph"
MIMETYPE = "application/hwp+zip"

_ALL_NS = (
    'xmlns:ha="http://www.hancom.co.kr/hwpml/2011/app" '
    'xmlns:hp="http://www.hancom.co.kr/hwpml/2011/paragraph" '
    'xmlns:hp10="http://www.hancom.co.kr/hwpml/2016/paragraph" '
    'xmlns:hs="http://www.hancom.co.kr/hwpml/2011/section" '
    'xmlns:hc="http://www.hancom.co.kr/hwpml/2011/core" '
    'xmlns:hh="http://www.hancom.co.kr/hwpml/2011/head" '
    'xmlns:hhs="http://www.hancom.co.kr/hwpml/2011/history" '
    'xmlns:hm="http://www.hancom.co.kr/hwpml/2011/master-page" '
    'xmlns:hpf="http://www.hancom.co.kr/schema/2011/hpf" '
    'xmlns:dc="http://purl.org/dc/elements/1.1/" '
    'xmlns:opf="http://www.idpf.org/2007/opf/" '
    'xmlns:ooxmlchart="http://www.hancom.co.kr/hwpml/2016/ooxmlchart" '
    'xmlns:hwpunitchar="http://www.hancom.co.kr/hwpml/2016/HwpUnitChar" '
    'xmlns:epub="http://www.idpf.org/2007/ops" '
    'xmlns:config="urn:oasis:names:tc:opendocument:xmlns:config:1.0"'
)

for _pfx, _uri in {
    "hp": HP_NS, "hs": HS_NS, "hc": HC_NS,
    "hh": HH_NS, "ha": HA_NS, "hv": HV_NS,
    "hpf": HPF_NS, "opf": OPF_NS,
}.items():
    etree.register_namespace(_pfx, _uri)

# ── 단락 스타일 ─────────────────────────────────────────────────────
PARA_STYLES = [
    (1, "제목", "Title", 2200, True, "CENTER", 0),
    (2, "부제목", "Subtitle", 1400, True, "CENTER", 200),
    (3, "제목1", "Heading 1", 1600, True, "LEFT", 400),
    (4, "제목2", "Heading 2", 1300, True, "LEFT", 300),
    (5, "제목3", "Heading 3", 1100, True, "LEFT", 200),
]


class HwpxService:
    """HWPX 읽기/쓰기/미리보기 서비스."""

    # ── 읽기 ────────────────────────────────────────────────────────

    def read_text(self, path: str | Path) -> str:
        """HWPX 파일에서 순수 텍스트 추출."""
        path = Path(path)
        all_text: list[str] = []
        with zipfile.ZipFile(path, "r") as zf:
            ns = self._discover_namespaces(zf)
            for section_file in self._get_section_files(zf):
                section_data = zf.read(section_file)
                if not ns:
                    ns = self._extract_namespaces_from_bytes(section_data)
                text = self._extract_text_from_section(section_data, ns)
                all_text.append(text)
        return "\n\n".join(all_text)

    def read_metadata(self, path: str | Path) -> dict:
        """메타데이터 추출."""
        path = Path(path)
        meta = {
            "filename": path.name,
            "format": "hwpx",
            "size_bytes": path.stat().st_size if path.exists() else 0,
        }
        try:
            with zipfile.ZipFile(path, "r") as zf:
                meta["section_count"] = len(self._get_section_files(zf))
                if "Contents/header.xml" in zf.namelist():
                    root = etree.fromstring(zf.read("Contents/header.xml"))
                    title_el = root.find(".//{http://purl.org/dc/elements/1.1/}title")
                    if title_el is not None and title_el.text:
                        meta["title"] = title_el.text
        except Exception:
            pass
        return meta

    def render_html(self, path: str | Path) -> str:
        """HWPX → HTML 미리보기 변환."""
        text = self.read_text(path)
        lines = text.split("\n")
        html_lines = []
        for line in lines:
            if not line.strip():
                html_lines.append("<p>&nbsp;</p>")
            else:
                escaped = (
                    line.replace("&", "&amp;")
                    .replace("<", "&lt;")
                    .replace(">", "&gt;")
                )
                html_lines.append(f"<p>{escaped}</p>")
        return (
            '<div style="font-family:\'Noto Serif KR\',serif;'
            'font-size:13px;line-height:2;padding:20px;">'
            + "\n".join(html_lines)
            + "</div>"
        )

    # ── 쓰기 (새 파일 생성) ─────────────────────────────────────────

    def create(self, path: str | Path, content: str) -> Path:
        """순수 텍스트로 새 HWPX 파일 생성."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)

        section_xml = self._build_section_xml(content)
        preview_text = self._extract_preview_text(content)

        # ZIP entry order matches known-working HWPX structure
        with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as zf:
            # 1. mimetype — STORED, must be first
            zf.writestr(
                zipfile.ZipInfo("mimetype"),
                MIMETYPE,
                compress_type=zipfile.ZIP_STORED,
            )
            # 2. version.xml — STORED (critical for Hancom parser)
            zf.writestr(
                zipfile.ZipInfo("version.xml"),
                self._version_xml(),
                compress_type=zipfile.ZIP_STORED,
            )
            # 3-4. Contents
            zf.writestr("Contents/header.xml", self._header_xml())
            zf.writestr("Contents/section0.xml", section_xml)
            # 5. Preview text
            zf.writestr("Preview/PrvText.txt", preview_text)
            # 6. settings
            zf.writestr("settings.xml", self._settings_xml())
            # 7-8. META-INF + content.hpf
            zf.writestr("META-INF/container.rdf", self._container_rdf())
            zf.writestr("Contents/content.hpf", self._content_hpf_xml())
            zf.writestr("META-INF/container.xml", self._container_xml())
            zf.writestr("META-INF/manifest.xml", self._manifest_xml())

        log.info("HWPX 생성 완료", path=str(path))
        return path

    # ── 템플릿 기반 생성 ─────────────────────────────────────────────

    def create_from_template(
        self,
        template_name: str,
        fields: dict[str, str],
        output_path: str | Path,
        templates_dir: str | Path = "data/templates",
    ) -> Path:
        """템플릿 HWPX에 필드를 채워 새 HWPX 생성."""
        template_path = Path(templates_dir) / f"{template_name}.hwpx"
        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)

        # 날짜 자동 주입 (RULE-01)
        today = date.today()
        fields.setdefault("기안일", f"{today.year}. {today.month}. {today.day}.")
        fields.setdefault("연도", str(today.year))

        if template_path.exists():
            shutil.copy2(template_path, output)
            self._replace_fields_in_hwpx(output, fields)
        else:
            # 템플릿 파일 없으면 내용으로 직접 생성
            body = fields.get("본문", "") or fields.get("내용", "")
            title = fields.get("제목", "") or fields.get("회의명", "")
            # 본문/제목 외 메타 필드도 문서에 포함
            meta_lines = []
            for key in ("일시", "장소", "참석자", "결정사항", "후속조치"):
                val = fields.get(key, "")
                if val:
                    meta_lines.append(f"{key}: {val}")
            meta_block = "\n".join(meta_lines)
            if title and meta_block:
                content = f"# {title}\n\n{meta_block}\n\n{body}"
            elif title:
                content = f"# {title}\n\n{body}"
            elif meta_block:
                content = f"{meta_block}\n\n{body}"
            else:
                content = body
            self.create(output, content)

        return output

    def _replace_fields_in_hwpx(self, path: Path, fields: dict[str, str]) -> None:
        """HWPX ZIP 내 모든 XML에서 {{필드명}} 치환."""
        tmp_dir = Path(tempfile.mkdtemp(prefix="hwpx_tpl_"))
        try:
            with zipfile.ZipFile(path, "r") as zf:
                zf.extractall(tmp_dir)

            for xml_file in tmp_dir.rglob("*"):
                if xml_file.is_file() and xml_file.suffix in (".xml", ".hpf"):
                    raw = xml_file.read_text(encoding="utf-8", errors="replace")
                    for key, val in fields.items():
                        raw = raw.replace(f"{{{{{key}}}}}", val)
                    xml_file.write_text(raw, encoding="utf-8")

            self._repack_hwpx(path, tmp_dir)
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)

    # ── 편집 ─────────────────────────────────────────────────────────

    def append_text(self, path: str | Path, text: str) -> Path:
        """기존 HWPX 파일 끝에 텍스트 추가."""
        path = Path(path)
        tmp_dir = Path(tempfile.mkdtemp(prefix="hwpx_edit_"))
        try:
            with zipfile.ZipFile(path, "r") as zf:
                zf.extractall(tmp_dir)

            section_files = sorted(
                (tmp_dir / "Contents").glob("section*.xml")
            )
            if not section_files:
                raise FileNotFoundError("HWPX에 섹션 파일이 없습니다.")

            self._op_append(section_files[-1], text)
            self._repack_hwpx(path, tmp_dir)
            return path
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)

    def replace_text(
        self, path: str | Path, search: str, replacement: str
    ) -> Path:
        """HWPX 파일 내 텍스트 치환."""
        path = Path(path)
        tmp_dir = Path(tempfile.mkdtemp(prefix="hwpx_edit_"))
        try:
            with zipfile.ZipFile(path, "r") as zf:
                zf.extractall(tmp_dir)

            for xml_file in (tmp_dir / "Contents").glob("section*.xml"):
                raw = xml_file.read_bytes().decode("utf-8")
                if search in raw:
                    raw = raw.replace(search, replacement)
                    xml_file.write_bytes(raw.encode("utf-8"))

            self._repack_hwpx(path, tmp_dir)
            return path
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)

    # ── 유효성 검사 ──────────────────────────────────────────────────

    def validate_hwpx(self, path: str | Path) -> dict:
        """HWPX 파일 유효성 검사."""
        try:
            with zipfile.ZipFile(path) as zf:
                names = zf.namelist()
                return {
                    "valid": (
                        "Contents/content.hpf" in names
                        or any("section" in n for n in names)
                    ),
                    "file_count": len(names),
                }
        except zipfile.BadZipFile:
            return {"valid": False, "error": "유효하지 않은 ZIP/HWPX 파일"}

    @staticmethod
    def _extract_preview_text(content: str, max_chars: int = 1000) -> str:
        """콘텐츠에서 미리보기 텍스트 생성 (Preview/PrvText.txt용)."""
        import re
        # 마크다운 서식 제거
        text = re.sub(r"[#*_`>|]", "", content)
        text = re.sub(r"-{3,}", "", text)
        text = re.sub(r"\s+", " ", text).strip()
        # CRLF 줄바꿈, 최대 길이 제한
        lines = content.split("\n")
        preview_lines = []
        total = 0
        for line in lines:
            clean = re.sub(r"[#*_`>|]", "", line).strip()
            if not clean:
                continue
            if total + len(clean) > max_chars:
                break
            preview_lines.append(clean)
            total += len(clean)
        return "\r\n".join(preview_lines) + "\r\n"

    # ═══════════════════════════════════════════════════════════════════
    # 내부 헬퍼 — 읽기
    # ═══════════════════════════════════════════════════════════════════

    @staticmethod
    def _get_section_files(zf: zipfile.ZipFile) -> list[str]:
        return sorted(
            n
            for n in zf.namelist()
            if n.startswith("Contents/section") and n.endswith(".xml")
        )

    @staticmethod
    def _discover_namespaces(zf: zipfile.ZipFile) -> dict[str, str]:
        for candidate in ("Contents/header.xml", "contents/header.xml"):
            if candidate in zf.namelist():
                data = zf.read(candidate)
                return HwpxService._extract_namespaces_from_bytes(data)
        return {}

    @staticmethod
    def _extract_namespaces_from_bytes(xml_data: bytes) -> dict[str, str]:
        ns: dict[str, str] = {}
        for event, elem in etree.iterparse(
            BytesIO(xml_data), events=("start-ns",)
        ):
            prefix, uri = elem
            if prefix:
                ns[prefix] = uri
        return ns

    @staticmethod
    def _extract_text_from_section(
        section_xml: bytes, ns: dict[str, str]
    ) -> str:
        root = etree.fromstring(section_xml)
        text_parts: list[str] = []
        hp_ns = ns.get("hp") or HP_NS

        paragraphs = root.findall(f".//{{{hp_ns}}}p")
        if not paragraphs and hp_ns != HP_NS_ALT:
            paragraphs = root.findall(f".//{{{HP_NS_ALT}}}p")
            if paragraphs:
                hp_ns = HP_NS_ALT

        if paragraphs:
            for para in paragraphs:
                para_texts: list[str] = []
                runs = para.findall(f".//{{{hp_ns}}}run")
                if not runs:
                    runs = para.findall(f".//{{{hp_ns}}}r")
                for run in runs:
                    t_elem = run.find(f"{{{hp_ns}}}t")
                    if t_elem is not None and t_elem.text:
                        para_texts.append(t_elem.text)
                if para_texts:
                    text_parts.append("".join(para_texts))
        else:
            text_parts = [t.strip() for t in root.itertext() if t.strip()]

        return "\n".join(text_parts)

    # ═══════════════════════════════════════════════════════════════════
    # 내부 헬퍼 — XML 생성
    # ═══════════════════════════════════════════════════════════════════

    @staticmethod
    def _parse_styled_line(line: str) -> tuple[str, int]:
        if line.startswith("##### "):
            return line[6:], 5
        if line.startswith("#### "):
            return line[5:], 4
        if line.startswith("### "):
            return line[4:], 3
        if line.startswith("## "):
            return line[3:], 2
        if line.startswith("# "):
            return line[2:], 1
        return line, 0

    @staticmethod
    def _build_section_xml(content: str) -> str:
        # First paragraph: 3 SEPARATE runs (secPr, ctrl, text)
        # This matches the working reference HWPX structure exactly.
        sec_pr_para = (
            '<hp:p id="0" paraPrIDRef="0" styleIDRef="0" pageBreak="0"'
            ' columnBreak="0" merged="0">'
            # Run 1: section properties only
            '<hp:run charPrIDRef="0">'
            '<hp:secPr textDirection="HORIZONTAL" spaceColumns="1134"'
            ' tabStop="8000" tabStopVal="4000" tabStopUnit="HWPUNIT"'
            ' outlineShapeIDRef="1" memoShapeIDRef="0"'
            ' textVerticalWidthHead="0">'
            '<hp:grid lineGrid="0" charGrid="0" wonggojiFormat="0"/>'
            '<hp:startNum pageStartsOn="BOTH" page="0" pic="0"'
            ' tbl="0" equation="0"/>'
            '<hp:visibility hideFirstHeader="0" hideFirstFooter="0"'
            ' hideFirstMasterPage="0" border="SHOW_ALL" fill="SHOW_ALL"'
            ' hideFirstPageNum="0" hideFirstEmptyLine="0"'
            ' showLineNumber="0"/>'
            '<hp:lineNumberShape restartType="0" countBy="0"'
            ' distance="0" startNumber="0"/>'
            '<hp:pagePr landscape="WIDELY" width="59528" height="84186"'
            ' gutterType="LEFT_ONLY">'
            '<hp:margin header="4252" footer="4252" gutter="0"'
            ' left="8504" right="8504" top="5668" bottom="4252"/>'
            '</hp:pagePr>'
            '<hp:footNotePr>'
            '<hp:autoNumFormat type="DIGIT" userChar="" prefixChar=""'
            ' suffixChar=")" supscript="0"/>'
            '<hp:noteLine length="-1" type="SOLID" width="0.12 mm"'
            ' color="#000000"/>'
            '<hp:noteSpacing betweenNotes="283" belowLine="567"'
            ' aboveLine="850"/>'
            '<hp:numbering type="CONTINUOUS" newNum="1"/>'
            '<hp:placement place="EACH_COLUMN" beneathText="0"/>'
            '</hp:footNotePr>'
            '<hp:endNotePr>'
            '<hp:autoNumFormat type="DIGIT" userChar="" prefixChar=""'
            ' suffixChar=")" supscript="0"/>'
            '<hp:noteLine length="14692344" type="SOLID" width="0.12 mm"'
            ' color="#000000"/>'
            '<hp:noteSpacing betweenNotes="0" belowLine="567"'
            ' aboveLine="850"/>'
            '<hp:numbering type="CONTINUOUS" newNum="1"/>'
            '<hp:placement place="END_OF_DOCUMENT" beneathText="0"/>'
            '</hp:endNotePr>'
            '<hp:pageBorderFill type="BOTH" borderFillIDRef="1"'
            ' textBorder="PAPER" headerInside="0" footerInside="0"'
            ' fillArea="PAPER">'
            '<hp:offset left="1417" right="1417" top="1417"'
            ' bottom="1417"/>'
            '</hp:pageBorderFill>'
            '<hp:pageBorderFill type="EVEN" borderFillIDRef="1"'
            ' textBorder="PAPER" headerInside="0" footerInside="0"'
            ' fillArea="PAPER">'
            '<hp:offset left="1417" right="1417" top="1417"'
            ' bottom="1417"/>'
            '</hp:pageBorderFill>'
            '<hp:pageBorderFill type="ODD" borderFillIDRef="1"'
            ' textBorder="PAPER" headerInside="0" footerInside="0"'
            ' fillArea="PAPER">'
            '<hp:offset left="1417" right="1417" top="1417"'
            ' bottom="1417"/>'
            '</hp:pageBorderFill>'
            '</hp:secPr>'
            '</hp:run>'
            # Run 2: column control only
            '<hp:run charPrIDRef="0">'
            '<hp:ctrl>'
            '<hp:colPr id="" type="NEWSPAPER" layout="LEFT"'
            ' colCount="1" sameSz="1" sameGap="0"/>'
            '</hp:ctrl>'
            '</hp:run>'
            # Run 3: empty text (content follows in subsequent paragraphs)
            '<hp:run charPrIDRef="0">'
            '<hp:t></hp:t>'
            '</hp:run>'
            '</hp:p>'
        )

        # Content paragraphs start with id=1
        para_elements = md_to_owpml_elements(content, start_id=1)

        return (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes" ?>'
            f"<hs:sec {_ALL_NS}>"
            f"{sec_pr_para}"
            f"{para_elements}"
            "</hs:sec>"
        )

    @staticmethod
    def _container_xml() -> str:
        return (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes" ?>'
            "<ocf:container"
            ' xmlns:ocf="urn:oasis:names:tc:opendocument:xmlns:container"'
            ' xmlns:hpf="http://www.hancom.co.kr/schema/2011/hpf">'
            "<ocf:rootfiles>"
            '<ocf:rootfile full-path="Contents/content.hpf"'
            ' media-type="application/hwpml-package+xml"/>'
            '<ocf:rootfile full-path="Preview/PrvText.txt"'
            ' media-type="text/plain"/>'
            '<ocf:rootfile full-path="META-INF/container.rdf"'
            ' media-type="application/rdf+xml"/>'
            "</ocf:rootfiles>"
            "</ocf:container>"
        )

    @staticmethod
    def _manifest_xml() -> str:
        return (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes" ?>'
            '<odf:manifest xmlns:odf='
            '"urn:oasis:names:tc:opendocument:xmlns:manifest:1.0"/>'
        )

    @staticmethod
    def _container_rdf() -> str:
        return (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes" ?>'
            '<rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">'
            '<rdf:Description rdf:about="">'
            '<ns0:hasPart xmlns:ns0='
            '"http://www.hancom.co.kr/hwpml/2016/meta/pkg#"'
            ' rdf:resource="Contents/header.xml"/>'
            '</rdf:Description>'
            '<rdf:Description rdf:about="Contents/header.xml">'
            '<rdf:type rdf:resource='
            '"http://www.hancom.co.kr/hwpml/2016/meta/pkg#HeaderFile"/>'
            '</rdf:Description>'
            '<rdf:Description rdf:about="">'
            '<ns0:hasPart xmlns:ns0='
            '"http://www.hancom.co.kr/hwpml/2016/meta/pkg#"'
            ' rdf:resource="Contents/section0.xml"/>'
            '</rdf:Description>'
            '<rdf:Description rdf:about="Contents/section0.xml">'
            '<rdf:type rdf:resource='
            '"http://www.hancom.co.kr/hwpml/2016/meta/pkg#SectionFile"/>'
            '</rdf:Description>'
            '<rdf:Description rdf:about="">'
            '<rdf:type rdf:resource='
            '"http://www.hancom.co.kr/hwpml/2016/meta/pkg#Document"/>'
            '</rdf:Description>'
            '</rdf:RDF>'
        )

    @staticmethod
    def _version_xml() -> str:
        return (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes" ?>'
            f'<hv:HCFVersion xmlns:hv="{HV_NS}"'
            ' tagetApplication="WORDPROCESSOR"'
            ' major="5" minor="1" micro="1" buildNumber="0"'
            ' os="1" xmlVersion="1.5"'
            ' application="Hancom Office Hangul"'
            ' appVersion="13, 0, 0, 3189 WIN32LEWindows_10"/>'
        )

    @staticmethod
    def _settings_xml() -> str:
        return (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes" ?>'
            f'<ha:HWPApplicationSetting xmlns:ha="{HA_NS}"'
            ' xmlns:config="urn:oasis:names:tc:opendocument:xmlns:config:1.0">'
            '<ha:CaretPosition listIDRef="0" paraIDRef="0" pos="0"/>'
            "</ha:HWPApplicationSetting>"
        )

    @staticmethod
    def _content_hpf_xml() -> str:
        return (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes" ?>'
            f"<opf:package {_ALL_NS}"
            ' version="" unique-identifier="" id="">'
            "<opf:metadata>"
            "<opf:title/>"
            "<opf:language>ko</opf:language>"
            '<opf:meta name="creator" content="text"/>'
            '<opf:meta name="subject" content="text"/>'
            '<opf:meta name="description" content="text"/>'
            '<opf:meta name="lastsaveby" content="text"/>'
            '<opf:meta name="CreatedDate" content="text">'
            "2026-01-01T00:00:00Z</opf:meta>"
            '<opf:meta name="ModifiedDate" content="text">'
            "2026-01-01T00:00:00Z</opf:meta>"
            '<opf:meta name="date" content="text">2026-01-01</opf:meta>'
            '<opf:meta name="keyword" content="text"/>'
            "</opf:metadata>"
            "<opf:manifest>"
            '<opf:item id="header" href="Contents/header.xml"'
            ' media-type="application/xml"/>'
            '<opf:item id="section0" href="Contents/section0.xml"'
            ' media-type="application/xml"/>'
            '<opf:item id="settings" href="settings.xml"'
            ' media-type="application/xml"/>'
            "</opf:manifest>"
            "<opf:spine>"
            '<opf:itemref idref="header" linear="yes"/>'
            '<opf:itemref idref="section0" linear="yes"/>'
            "</opf:spine>"
            "</opf:package>"
        )

    @staticmethod
    def _header_xml() -> str:
        font_type_info = (
            '<hh:typeInfo familyType="FCAT_GOTHIC" weight="6"'
            ' proportion="4" contrast="0" strokeVariation="1"'
            ' armStyle="1" letterform="1" midline="1" xHeight="1"/>'
        )
        font_entry = (
            '<hh:font id="0" face="\ud568\ucd08\ub86c\ub3cb\uc6c0"'
            f' type="TTF" isEmbedded="0">{font_type_info}</hh:font>'
            '<hh:font id="1" face="\ud568\ucd08\ub86c\ubc14\ud0d5"'
            f' type="TTF" isEmbedded="0">{font_type_info}</hh:font>'
        )
        fontfaces = ""
        for lang in (
            "HANGUL", "LATIN", "HANJA", "JAPANESE",
            "OTHER", "SYMBOL", "USER",
        ):
            fontfaces += f'<hh:fontface lang="{lang}" fontCnt="2">{font_entry}</hh:fontface>'

        extra_char = _build_extra_char_properties()
        extra_para = _build_extra_para_properties()
        extra_styles = _build_extra_styles()

        # Counts: id=0 + 5 styles + id=6(bold) = 7 charPr
        num_char = 1 + len(PARA_STYLES) + 1
        # Counts: id=0 + 5 styles = 6 paraPr
        num_para = 1 + len(PARA_STYLES)
        # Counts: id=0(Normal) + 5 styles = 6 styles
        num_styles = 1 + len(PARA_STYLES)
        # borderFills: 4 (ids 1-4)
        num_bf = 4

        return (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes" ?>'
            f'<hh:head {_ALL_NS} version="1.5" secCnt="1">'
            '<hh:beginNum page="1" footnote="1" endnote="1"'
            ' pic="1" tbl="1" equation="1"/>'
            "<hh:refList>"
            f'<hh:fontfaces itemCnt="7">{fontfaces}</hh:fontfaces>'
            f'<hh:borderFills itemCnt="{num_bf}">'
            '<hh:borderFill id="1" threeD="0" shadow="0"'
            ' centerLine="NONE" breakCellSeparateLine="0">'
            '<hh:slash type="NONE" Crooked="0" isCounter="0"/>'
            '<hh:backSlash type="NONE" Crooked="0" isCounter="0"/>'
            '<hh:leftBorder type="NONE" width="0.1 mm" color="#000000"/>'
            '<hh:rightBorder type="NONE" width="0.1 mm" color="#000000"/>'
            '<hh:topBorder type="NONE" width="0.1 mm" color="#000000"/>'
            '<hh:bottomBorder type="NONE" width="0.1 mm" color="#000000"/>'
            '<hh:diagonal type="SOLID" width="0.1 mm" color="#000000"/>'
            "</hh:borderFill>"
            '<hh:borderFill id="2" threeD="0" shadow="0"'
            ' centerLine="NONE" breakCellSeparateLine="0">'
            '<hh:slash type="NONE" Crooked="0" isCounter="0"/>'
            '<hh:backSlash type="NONE" Crooked="0" isCounter="0"/>'
            '<hh:leftBorder type="NONE" width="0.1 mm" color="#000000"/>'
            '<hh:rightBorder type="NONE" width="0.1 mm" color="#000000"/>'
            '<hh:topBorder type="NONE" width="0.1 mm" color="#000000"/>'
            '<hh:bottomBorder type="NONE" width="0.1 mm" color="#000000"/>'
            '<hh:diagonal type="SOLID" width="0.1 mm" color="#000000"/>'
            "<hc:fillBrush>"
            '<hc:winBrush faceColor="none"'
            ' hatchColor="#FF000000" alpha="0"/>'
            "</hc:fillBrush>"
            "</hh:borderFill>"
            '<hh:borderFill id="3" threeD="0" shadow="0"'
            ' centerLine="NONE" breakCellSeparateLine="0">'
            '<hh:slash type="NONE" Crooked="0" isCounter="0"/>'
            '<hh:backSlash type="NONE" Crooked="0" isCounter="0"/>'
            '<hh:leftBorder type="SOLID" width="0.12 mm" color="#000000"/>'
            '<hh:rightBorder type="SOLID" width="0.12 mm" color="#000000"/>'
            '<hh:topBorder type="SOLID" width="0.12 mm" color="#000000"/>'
            '<hh:bottomBorder type="SOLID" width="0.12 mm" color="#000000"/>'
            '<hh:diagonal type="NONE" width="0.1 mm" color="#000000"/>'
            "</hh:borderFill>"
            '<hh:borderFill id="4" threeD="0" shadow="0"'
            ' centerLine="NONE" breakCellSeparateLine="0">'
            '<hh:slash type="NONE" Crooked="0" isCounter="0"/>'
            '<hh:backSlash type="NONE" Crooked="0" isCounter="0"/>'
            '<hh:leftBorder type="SOLID" width="0.12 mm" color="#000000"/>'
            '<hh:rightBorder type="SOLID" width="0.12 mm" color="#000000"/>'
            '<hh:topBorder type="SOLID" width="0.12 mm" color="#000000"/>'
            '<hh:bottomBorder type="SOLID" width="0.12 mm" color="#000000"/>'
            '<hh:diagonal type="NONE" width="0.1 mm" color="#000000"/>'
            "<hc:fillBrush>"
            '<hc:winBrush faceColor="#E8EDF3"'
            ' hatchColor="#FF000000" alpha="0"/>'
            "</hc:fillBrush>"
            "</hh:borderFill>"
            "</hh:borderFills>"
            f'<hh:charProperties itemCnt="{num_char}">'
            '<hh:charPr id="0" height="1000" textColor="#000000"'
            ' shadeColor="none" useFontSpace="0" useKerning="0"'
            ' symMark="NONE" borderFillIDRef="2">'
            '<hh:fontRef hangul="0" latin="0" hanja="0" japanese="0"'
            ' other="0" symbol="0" user="0"/>'
            '<hh:ratio hangul="100" latin="100" hanja="100"'
            ' japanese="100" other="100" symbol="100" user="100"/>'
            '<hh:spacing hangul="0" latin="0" hanja="0"'
            ' japanese="0" other="0" symbol="0" user="0"/>'
            '<hh:relSz hangul="100" latin="100" hanja="100"'
            ' japanese="100" other="100" symbol="100" user="100"/>'
            '<hh:offset hangul="0" latin="0" hanja="0"'
            ' japanese="0" other="0" symbol="0" user="0"/>'
            '<hh:underline type="NONE" shape="SOLID" color="#000000"/>'
            '<hh:strikeout shape="NONE" color="#000000"/>'
            '<hh:outline type="NONE"/>'
            '<hh:shadow type="NONE" color="#B2B2B2"'
            ' offsetX="10" offsetY="10"/>'
            "</hh:charPr>"
            f"{extra_char}"
            '<hh:charPr id="6" height="1000" textColor="#000000"'
            ' shadeColor="none" useFontSpace="0" useKerning="0"'
            ' symMark="NONE" borderFillIDRef="2">'
            '<hh:fontRef hangul="0" latin="0" hanja="0" japanese="0"'
            ' other="0" symbol="0" user="0"/>'
            '<hh:ratio hangul="100" latin="100" hanja="100"'
            ' japanese="100" other="100" symbol="100" user="100"/>'
            '<hh:spacing hangul="0" latin="0" hanja="0"'
            ' japanese="0" other="0" symbol="0" user="0"/>'
            '<hh:relSz hangul="100" latin="100" hanja="100"'
            ' japanese="100" other="100" symbol="100" user="100"/>'
            '<hh:offset hangul="0" latin="0" hanja="0"'
            ' japanese="0" other="0" symbol="0" user="0"/>'
            '<hh:bold/>'
            '<hh:underline type="NONE" shape="SOLID" color="#000000"/>'
            '<hh:strikeout shape="NONE" color="#000000"/>'
            '<hh:outline type="NONE"/>'
            '<hh:shadow type="NONE" color="#B2B2B2"'
            ' offsetX="10" offsetY="10"/>'
            "</hh:charPr>"
            "</hh:charProperties>"
            '<hh:tabProperties itemCnt="2">'
            '<hh:tabPr id="0" autoTabLeft="0" autoTabRight="0"/>'
            '<hh:tabPr id="1" autoTabLeft="1" autoTabRight="0"/>'
            "</hh:tabProperties>"
            '<hh:numberings itemCnt="1">'
            '<hh:numbering id="1" start="0">'
            '<hh:paraHead start="1" level="1" align="LEFT"'
            ' useInstWidth="1" autoIndent="1" widthAdjust="0"'
            ' textOffsetType="PERCENT" textOffset="50"'
            ' numFormat="DIGIT" charPrIDRef="4294967295"'
            ' checkable="0">^1.</hh:paraHead>'
            "</hh:numbering>"
            "</hh:numberings>"
            f'<hh:paraProperties itemCnt="{num_para}">'
            '<hh:paraPr id="0" tabPrIDRef="0" condense="0"'
            ' fontLineHeight="0" snapToGrid="1"'
            ' suppressLineNumbers="0" checked="0">'
            '<hh:align horizontal="LEFT" vertical="BASELINE"/>'
            '<hh:heading type="NONE" idRef="0" level="0"/>'
            '<hh:breakSetting breakLatinWord="KEEP_WORD"'
            ' breakNonLatinWord="BREAK_WORD" widowOrphan="0"'
            ' keepWithNext="0" keepLines="0" pageBreakBefore="0"'
            ' lineWrap="BREAK"/>'
            '<hh:autoSpacing eAsianEng="0" eAsianNum="0"/>'
            "<hh:margin>"
            '<hc:intent value="0" unit="HWPUNIT"/>'
            '<hc:left value="0" unit="HWPUNIT"/>'
            '<hc:right value="0" unit="HWPUNIT"/>'
            '<hc:prev value="0" unit="HWPUNIT"/>'
            '<hc:next value="0" unit="HWPUNIT"/>'
            "</hh:margin>"
            '<hh:lineSpacing type="PERCENT" value="160"'
            ' unit="HWPUNIT"/>'
            '<hh:border borderFillIDRef="2" offsetLeft="0"'
            ' offsetRight="0" offsetTop="0" offsetBottom="0"'
            ' connect="0" ignoreMargin="0"/>'
            "</hh:paraPr>"
            f"{extra_para}"
            "</hh:paraProperties>"
            f'<hh:styles itemCnt="{num_styles}">'
            '<hh:style id="0" type="PARA"'
            ' name="\ubc14\ud0d5\uae00" engName="Normal"'
            ' paraPrIDRef="0" charPrIDRef="0" nextStyleIDRef="0"'
            ' langID="1042" lockForm="0"/>'
            f"{extra_styles}"
            "</hh:styles>"
            '<hh:memoProperties itemCnt="0"/>'
            '<hh:trackChangeAuthors itemCnt="0"/>'
            '<hh:trackChanges itemCnt="0"/>'
            "</hh:refList>"
            '<hh:compatibleDocument targetProgram="HWP201X">'
            "<hh:layoutCompatibility/>"
            "</hh:compatibleDocument>"
            "<hh:docOption>"
            '<hh:linkinfo path="" pageInherit="0" footnoteInherit="0"/>'
            "</hh:docOption>"
            '<hh:trackchageConfig flags="0"/>'
            "</hh:head>"
        )

    # ═══════════════════════════════════════════════════════════════════
    # 내부 헬퍼 — REPACK / EDIT
    # ═══════════════════════════════════════════════════════════════════

    @staticmethod
    def _repack_hwpx(filepath: Path, source_dir: Path) -> None:
        mimetype_file = source_dir / "mimetype"
        with zipfile.ZipFile(filepath, "w", zipfile.ZIP_DEFLATED) as zf:
            if mimetype_file.exists():
                zf.writestr(
                    zipfile.ZipInfo("mimetype"),
                    mimetype_file.read_text(encoding="utf-8"),
                    compress_type=zipfile.ZIP_STORED,
                )
            for file_path in sorted(source_dir.rglob("*")):
                if file_path.is_file() and file_path.name != "mimetype":
                    arcname = str(
                        file_path.relative_to(source_dir)
                    ).replace("\\", "/")
                    zf.write(file_path, arcname)

    def _op_append(self, section_path: Path, text: str) -> None:
        tree = etree.parse(str(section_path))
        root = tree.getroot()
        for line in text.split("\n"):
            p = etree.SubElement(root, f"{{{HP_NS}}}p")
            p.set("paraPrIDRef", "0")
            p.set("styleIDRef", "0")
            p.set("pageBreak", "0")
            p.set("columnBreak", "0")
            p.set("merged", "0")
            run = etree.SubElement(p, f"{{{HP_NS}}}run")
            run.set("charPrIDRef", "0")
            t = etree.SubElement(run, f"{{{HP_NS}}}t")
            t.text = line
        tree.write(str(section_path), xml_declaration=True, encoding="UTF-8")


# ── 모듈 수준 헬퍼 (header.xml 생성용) ──────────────────────────────

def _build_extra_char_properties() -> str:
    parts: list[str] = []
    for sid, _name, _eng, height, bold, _align, _mprev in PARA_STYLES:
        # bold is a child element <hh:bold/>, NOT an attribute
        bold_elem = "<hh:bold/>" if bold else ""
        parts.append(
            f'<hh:charPr id="{sid}" height="{height}" textColor="#000000"'
            f' shadeColor="none" useFontSpace="0" useKerning="0"'
            f' symMark="NONE" borderFillIDRef="2">'
            '<hh:fontRef hangul="0" latin="0" hanja="0" japanese="0"'
            ' other="0" symbol="0" user="0"/>'
            '<hh:ratio hangul="100" latin="100" hanja="100"'
            ' japanese="100" other="100" symbol="100" user="100"/>'
            '<hh:spacing hangul="0" latin="0" hanja="0"'
            ' japanese="0" other="0" symbol="0" user="0"/>'
            '<hh:relSz hangul="100" latin="100" hanja="100"'
            ' japanese="100" other="100" symbol="100" user="100"/>'
            '<hh:offset hangul="0" latin="0" hanja="0"'
            ' japanese="0" other="0" symbol="0" user="0"/>'
            f'{bold_elem}'
            '<hh:underline type="NONE" shape="SOLID" color="#000000"/>'
            '<hh:strikeout shape="NONE" color="#000000"/>'
            '<hh:outline type="NONE"/>'
            '<hh:shadow type="NONE" color="#B2B2B2"'
            ' offsetX="10" offsetY="10"/>'
            "</hh:charPr>"
        )
    return "".join(parts)


def _build_extra_para_properties() -> str:
    parts: list[str] = []
    for sid, _name, _eng, _height, _bold, align, margin_prev in PARA_STYLES:
        parts.append(
            f'<hh:paraPr id="{sid}" tabPrIDRef="0" condense="0"'
            ' fontLineHeight="0" snapToGrid="1"'
            ' suppressLineNumbers="0" checked="0">'
            f'<hh:align horizontal="{align}" vertical="BASELINE"/>'
            '<hh:heading type="NONE" idRef="0" level="0"/>'
            '<hh:breakSetting breakLatinWord="KEEP_WORD"'
            ' breakNonLatinWord="BREAK_WORD" widowOrphan="0"'
            ' keepWithNext="0" keepLines="0" pageBreakBefore="0"'
            ' lineWrap="BREAK"/>'
            '<hh:autoSpacing eAsianEng="0" eAsianNum="0"/>'
            "<hh:margin>"
            '<hc:intent value="0" unit="HWPUNIT"/>'
            '<hc:left value="0" unit="HWPUNIT"/>'
            '<hc:right value="0" unit="HWPUNIT"/>'
            f'<hc:prev value="{margin_prev}" unit="HWPUNIT"/>'
            '<hc:next value="0" unit="HWPUNIT"/>'
            "</hh:margin>"
            '<hh:lineSpacing type="PERCENT" value="160"'
            ' unit="HWPUNIT"/>'
            '<hh:border borderFillIDRef="2" offsetLeft="0"'
            ' offsetRight="0" offsetTop="0" offsetBottom="0"'
            ' connect="0" ignoreMargin="0"/>'
            "</hh:paraPr>"
        )
    return "".join(parts)


def _build_extra_styles() -> str:
    parts: list[str] = []
    for sid, name, eng_name, _height, _bold, _align, _mprev in PARA_STYLES:
        parts.append(
            f'<hh:style id="{sid}" type="PARA"'
            f' name="{name}" engName="{eng_name}"'
            f' paraPrIDRef="{sid}" charPrIDRef="{sid}"'
            f' nextStyleIDRef="0" langID="1042" lockForm="0"/>'
        )
    return "".join(parts)


# 모듈 수준 싱글턴
hwpx_service = HwpxService()
