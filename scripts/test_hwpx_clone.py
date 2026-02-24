"""Clone a working HWPX and replace section0.xml with test content.

This isolates whether our section0.xml structure is valid.
If the clone opens correctly → our section structure is OK, issue is elsewhere.
If the clone fails → our paragraph structure is wrong.

Also generates a fully-fixed HWPX from scratch for comparison.
"""

import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = ROOT / "data" / "workspace"

# Accept reference HWPX as CLI argument, or fall back to default location
if len(sys.argv) > 1:
    REFERENCE = Path(sys.argv[1])
else:
    REFERENCE = ROOT / "data" / "samples" / "gianmun" / "reference.hwpx"

ALL_NS = (
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

SEC_PR = (
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
)


def make_test_section() -> str:
    """Simple test section matching working reference paragraph structure."""
    # First paragraph: 3 SEPARATE runs (secPr, ctrl, text)
    first_para = (
        '<hp:p id="0" paraPrIDRef="0" styleIDRef="0"'
        ' pageBreak="0" columnBreak="0" merged="0">'
        # Run 1: section properties
        '<hp:run charPrIDRef="0">'
        f'{SEC_PR}'
        '</hp:run>'
        # Run 2: column control
        '<hp:run charPrIDRef="0">'
        '<hp:ctrl>'
        '<hp:colPr id="" type="NEWSPAPER" layout="LEFT"'
        ' colCount="1" sameSz="1" sameGap="0"/>'
        '</hp:ctrl>'
        '</hp:run>'
        # Run 3: actual text
        '<hp:run charPrIDRef="0">'
        '<hp:t>테스트 문서</hp:t>'
        '</hp:run>'
        '</hp:p>'
    )

    paras = [
        (1, "이 문서는 GM-AI-Hub에서 자동 생성한 테스트 문서입니다."),
        (2, ""),
        (3, "한컴오피스에서 정상적으로 열리는지 확인합니다."),
        (4, "문서 생성 시스템이 올바르게 작동하고 있습니다."),
    ]

    content_paras = ""
    for pid, text in paras:
        content_paras += (
            f'<hp:p id="{pid}" paraPrIDRef="0" styleIDRef="0"'
            f' pageBreak="0" columnBreak="0" merged="0">'
            f'<hp:run charPrIDRef="0">'
            f'<hp:t>{text}</hp:t>'
            f'</hp:run>'
            f'</hp:p>'
        )

    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes" ?>'
        f'<hs:sec {ALL_NS}>'
        f'{first_para}'
        f'{content_paras}'
        '</hs:sec>'
    )


def clone_test():
    """Test 1: Clone working HWPX, replace section0.xml only."""
    if not REFERENCE.exists():
        print(f"ERROR: Reference file not found: {REFERENCE}")
        return

    output = OUTPUT_DIR / "test_clone.hwpx"
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Read all entries from reference
    with zipfile.ZipFile(REFERENCE, "r") as ref_zf:
        entries = ref_zf.infolist()
        contents = {}
        for entry in entries:
            contents[entry.filename] = {
                "data": ref_zf.read(entry.filename),
                "compress_type": entry.compress_type,
            }

    # Replace section0.xml with our test content
    test_section = make_test_section()
    contents["Contents/section0.xml"]["data"] = test_section.encode("utf-8")

    # Also update Preview/PrvText.txt
    if "Preview/PrvText.txt" in contents:
        preview = (
            "테스트 문서\r\n"
            "이 문서는 GM-AI-Hub에서 자동 생성한 테스트 문서입니다.\r\n"
            "한컴오피스에서 정상적으로 열리는지 확인합니다.\r\n"
            "문서 생성 시스템이 올바르게 작동하고 있습니다.\r\n"
        )
        contents["Preview/PrvText.txt"]["data"] = preview.encode("utf-8")

    # Write output matching exact same entry order and compression
    with zipfile.ZipFile(output, "w") as zf:
        for entry in entries:
            fn = entry.filename
            info = zipfile.ZipInfo(fn)
            info.compress_type = contents[fn]["compress_type"]
            zf.writestr(info, contents[fn]["data"])

    print(f"[Clone] Written: {output}")
    print(f"[Clone] Size: {output.stat().st_size} bytes")
    print(f"[Clone] Uses working header.xml, replaced section0.xml only")

    # Verify ZIP structure
    with zipfile.ZipFile(output) as zf:
        for info in zf.infolist():
            method = "STORED" if info.compress_type == 0 else "DEFLATED"
            print(f"  {info.filename:40s} {method:8s} {info.file_size:>8d}")


def from_scratch_test():
    """Test 2: Generate HWPX completely from scratch, matching reference structure."""
    output = OUTPUT_DIR / "test_scratch.hwpx"
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    mimetype = "application/hwp+zip"

    version_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes" ?>'
        '<hv:HCFVersion xmlns:hv="http://www.hancom.co.kr/hwpml/2011/version"'
        ' tagetApplication="WORDPROCESSOR"'
        ' major="5" minor="1" micro="1" buildNumber="0"'
        ' os="1" xmlVersion="1.5"'
        ' application="Hancom Office Hangul"'
        ' appVersion="13, 0, 0, 3189 WIN32LEWindows_10"/>'
    )

    container_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes" ?>'
        '<ocf:container'
        ' xmlns:ocf="urn:oasis:names:tc:opendocument:xmlns:container"'
        ' xmlns:hpf="http://www.hancom.co.kr/schema/2011/hpf">'
        '<ocf:rootfiles>'
        '<ocf:rootfile full-path="Contents/content.hpf"'
        ' media-type="application/hwpml-package+xml"/>'
        '<ocf:rootfile full-path="Preview/PrvText.txt"'
        ' media-type="text/plain"/>'
        '<ocf:rootfile full-path="META-INF/container.rdf"'
        ' media-type="application/rdf+xml"/>'
        '</ocf:rootfiles>'
        '</ocf:container>'
    )

    manifest_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes" ?>'
        '<odf:manifest xmlns:odf='
        '"urn:oasis:names:tc:opendocument:xmlns:manifest:1.0"/>'
    )

    container_rdf = (
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

    content_hpf = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes" ?>'
        f'<opf:package {ALL_NS}'
        ' version="" unique-identifier="" id="">'
        '<opf:metadata>'
        '<opf:title>테스트 문서</opf:title>'
        '<opf:language>ko</opf:language>'
        '<opf:meta name="creator" content="text">GM-AI-Hub</opf:meta>'
        '<opf:meta name="subject" content="text"/>'
        '<opf:meta name="description" content="text"/>'
        '<opf:meta name="lastsaveby" content="text">GM-AI-Hub</opf:meta>'
        '<opf:meta name="CreatedDate" content="text">'
        '2026-02-21T00:00:00Z</opf:meta>'
        '<opf:meta name="ModifiedDate" content="text">'
        '2026-02-21T00:00:00Z</opf:meta>'
        '<opf:meta name="date" content="text">2026-02-21</opf:meta>'
        '<opf:meta name="keyword" content="text"/>'
        '</opf:metadata>'
        '<opf:manifest>'
        '<opf:item id="header" href="Contents/header.xml"'
        ' media-type="application/xml"/>'
        '<opf:item id="section0" href="Contents/section0.xml"'
        ' media-type="application/xml"/>'
        '<opf:item id="settings" href="settings.xml"'
        ' media-type="application/xml"/>'
        '</opf:manifest>'
        '<opf:spine>'
        '<opf:itemref idref="header" linear="yes"/>'
        '<opf:itemref idref="section0" linear="yes"/>'
        '</opf:spine>'
        '</opf:package>'
    )

    settings_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes" ?>'
        '<ha:HWPApplicationSetting'
        ' xmlns:ha="http://www.hancom.co.kr/hwpml/2011/app"'
        ' xmlns:config='
        '"urn:oasis:names:tc:opendocument:xmlns:config:1.0">'
        '<ha:CaretPosition listIDRef="0" paraIDRef="0" pos="0"/>'
        '</ha:HWPApplicationSetting>'
    )

    preview_text = (
        "테스트 문서\r\n"
        "이 문서는 GM-AI-Hub에서 자동 생성한 테스트 문서입니다.\r\n"
        "한컴오피스에서 정상적으로 열리는지 확인합니다.\r\n"
        "문서 생성 시스템이 올바르게 작동하고 있습니다.\r\n"
    )

    section_xml = make_test_section()

    # Use working reference header.xml if available, else generate minimal
    header_xml = None
    if REFERENCE.exists():
        with zipfile.ZipFile(REFERENCE) as ref_zf:
            if "Contents/header.xml" in ref_zf.namelist():
                header_xml = ref_zf.read("Contents/header.xml")
                print("[Scratch] Using header.xml from working reference")

    if header_xml is None:
        header_xml = _make_minimal_header().encode("utf-8")
        print("[Scratch] Using generated minimal header.xml")

    # Write HWPX matching working file structure
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as zf:
        # 1. mimetype - STORED (MUST be first)
        info = zipfile.ZipInfo("mimetype")
        zf.writestr(info, mimetype, compress_type=zipfile.ZIP_STORED)

        # 2. version.xml - STORED (critical!)
        info = zipfile.ZipInfo("version.xml")
        zf.writestr(info, version_xml, compress_type=zipfile.ZIP_STORED)

        # 3. Contents/header.xml - DEFLATED
        zf.writestr("Contents/header.xml", header_xml)

        # 4. Contents/section0.xml - DEFLATED
        zf.writestr("Contents/section0.xml", section_xml)

        # 5. Preview/PrvText.txt - DEFLATED
        zf.writestr("Preview/PrvText.txt", preview_text)

        # 6. settings.xml - DEFLATED
        zf.writestr("settings.xml", settings_xml)

        # 7. META-INF/container.rdf - DEFLATED
        zf.writestr("META-INF/container.rdf", container_rdf)

        # 8. Contents/content.hpf - DEFLATED
        zf.writestr("Contents/content.hpf", content_hpf)

        # 9. META-INF/container.xml - DEFLATED
        zf.writestr("META-INF/container.xml", container_xml)

        # 10. META-INF/manifest.xml - DEFLATED
        zf.writestr("META-INF/manifest.xml", manifest_xml)

    print(f"[Scratch] Written: {output}")
    print(f"[Scratch] Size: {output.stat().st_size} bytes")

    # Verify
    with zipfile.ZipFile(output) as zf:
        for info in zf.infolist():
            method = "STORED" if info.compress_type == 0 else "DEFLATED"
            print(f"  {info.filename:40s} {method:8s} {info.file_size:>8d}")


def _make_minimal_header() -> str:
    """Minimal header.xml matching working reference structure."""
    font_type = (
        '<hh:typeInfo familyType="FCAT_GOTHIC" weight="6"'
        ' proportion="4" contrast="0" strokeVariation="1"'
        ' armStyle="1" letterform="1" midline="1" xHeight="1"/>'
    )
    font_entries = (
        '<hh:font id="0" face="\ud568\ucd08\ub86c\ub3cb\uc6c0"'
        f' type="TTF" isEmbedded="0">{font_type}</hh:font>'
        '<hh:font id="1" face="\ud568\ucd08\ub86c\ubc14\ud0d5"'
        f' type="TTF" isEmbedded="0">{font_type}</hh:font>'
    )
    fontfaces = ""
    for lang in ("HANGUL", "LATIN", "HANJA", "JAPANESE",
                 "OTHER", "SYMBOL", "USER"):
        fontfaces += (
            f'<hh:fontface lang="{lang}" fontCnt="2">'
            f'{font_entries}</hh:fontface>'
        )

    char_pr_base = (
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
    )

    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes" ?>'
        f'<hh:head {ALL_NS} version="1.5" secCnt="1">'
        '<hh:beginNum page="1" footnote="1" endnote="1"'
        ' pic="1" tbl="1" equation="1"/>'
        '<hh:refList>'
        f'<hh:fontfaces itemCnt="7">{fontfaces}</hh:fontfaces>'
        '<hh:borderFills itemCnt="2">'
        '<hh:borderFill id="1" threeD="0" shadow="0"'
        ' centerLine="NONE" breakCellSeparateLine="0">'
        '<hh:slash type="NONE" Crooked="0" isCounter="0"/>'
        '<hh:backSlash type="NONE" Crooked="0" isCounter="0"/>'
        '<hh:leftBorder type="NONE" width="0.1 mm" color="#000000"/>'
        '<hh:rightBorder type="NONE" width="0.1 mm" color="#000000"/>'
        '<hh:topBorder type="NONE" width="0.1 mm" color="#000000"/>'
        '<hh:bottomBorder type="NONE" width="0.1 mm" color="#000000"/>'
        '<hh:diagonal type="SOLID" width="0.1 mm" color="#000000"/>'
        '</hh:borderFill>'
        '<hh:borderFill id="2" threeD="0" shadow="0"'
        ' centerLine="NONE" breakCellSeparateLine="0">'
        '<hh:slash type="NONE" Crooked="0" isCounter="0"/>'
        '<hh:backSlash type="NONE" Crooked="0" isCounter="0"/>'
        '<hh:leftBorder type="NONE" width="0.1 mm" color="#000000"/>'
        '<hh:rightBorder type="NONE" width="0.1 mm" color="#000000"/>'
        '<hh:topBorder type="NONE" width="0.1 mm" color="#000000"/>'
        '<hh:bottomBorder type="NONE" width="0.1 mm" color="#000000"/>'
        '<hh:diagonal type="SOLID" width="0.1 mm" color="#000000"/>'
        '<hc:fillBrush>'
        '<hc:winBrush faceColor="none"'
        ' hatchColor="#FF000000" alpha="0"/>'
        '</hc:fillBrush>'
        '</hh:borderFill>'
        '</hh:borderFills>'
        '<hh:charProperties itemCnt="1">'
        '<hh:charPr id="0" height="1000" textColor="#000000"'
        ' shadeColor="none" useFontSpace="0" useKerning="0"'
        ' symMark="NONE" borderFillIDRef="2">'
        f'{char_pr_base}'
        '</hh:charPr>'
        '</hh:charProperties>'
        '<hh:tabProperties itemCnt="1">'
        '<hh:tabPr id="0" autoTabLeft="0" autoTabRight="0"/>'
        '</hh:tabProperties>'
        '<hh:numberings itemCnt="1">'
        '<hh:numbering id="1" start="0">'
        '<hh:paraHead start="1" level="1" align="LEFT"'
        ' useInstWidth="1" autoIndent="1" widthAdjust="0"'
        ' textOffsetType="PERCENT" textOffset="50"'
        ' numFormat="DIGIT" charPrIDRef="4294967295"'
        ' checkable="0">^1.</hh:paraHead>'
        '</hh:numbering>'
        '</hh:numberings>'
        '<hh:paraProperties itemCnt="1">'
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
        '<hh:margin>'
        '<hc:intent value="0" unit="HWPUNIT"/>'
        '<hc:left value="0" unit="HWPUNIT"/>'
        '<hc:right value="0" unit="HWPUNIT"/>'
        '<hc:prev value="0" unit="HWPUNIT"/>'
        '<hc:next value="0" unit="HWPUNIT"/>'
        '</hh:margin>'
        '<hh:lineSpacing type="PERCENT" value="160"'
        ' unit="HWPUNIT"/>'
        '<hh:border borderFillIDRef="2" offsetLeft="0"'
        ' offsetRight="0" offsetTop="0" offsetBottom="0"'
        ' connect="0" ignoreMargin="0"/>'
        '</hh:paraPr>'
        '</hh:paraProperties>'
        '<hh:styles itemCnt="1">'
        '<hh:style id="0" type="PARA"'
        ' name="\ubc14\ud0d5\uae00" engName="Normal"'
        ' paraPrIDRef="0" charPrIDRef="0" nextStyleIDRef="0"'
        ' langID="1042" lockForm="0"/>'
        '</hh:styles>'
        '<hh:memoProperties itemCnt="0"/>'
        '<hh:trackChangeAuthors itemCnt="0"/>'
        '<hh:trackChanges itemCnt="0"/>'
        '</hh:refList>'
        '<hh:compatibleDocument targetProgram="HWP201X">'
        '<hh:layoutCompatibility/>'
        '</hh:compatibleDocument>'
        '<hh:docOption>'
        '<hh:linkinfo path="" pageInherit="0" footnoteInherit="0"/>'
        '</hh:docOption>'
        '<hh:trackchageConfig flags="0"/>'
        '</hh:head>'
    )


if __name__ == "__main__":
    print("=" * 60)
    print("HWPX Test File Generator")
    print("=" * 60)

    print("\n--- Test 1: Clone from working reference ---")
    clone_test()

    print("\n--- Test 2: From scratch (with reference header) ---")
    from_scratch_test()

    print("\n" + "=" * 60)
    print("Please test both files in Hancom Office:")
    print(f"  1. {OUTPUT_DIR / 'test_clone.hwpx'}")
    print(f"  2. {OUTPUT_DIR / 'test_scratch.hwpx'}")
    print("=" * 60)
