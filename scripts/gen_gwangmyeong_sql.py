"""Parse extracted ordinance text and generate SQL migration 006."""
import re
from pathlib import Path

ROOT = Path(__file__).parent.parent

LAW_NAMES = {
    "광명시공유경제활성화에관한조례.pdf": "광명시 공유경제 활성화에 관한 조례",
    "광명시공유경제활성화에관한조례시행규칙.pdf": "광명시 공유경제 활성화에 관한 조례 시행규칙",
    "광명시공정무역지원및육성에관한조례.pdf": "광명시 공정무역 지원 및 육성에 관한 조례",
    "광명시사회적기업육성및지원에관한조례.pdf": "광명시 사회적기업 육성 및 지원에 관한 조례",
    "광명시성인문해교육의공공성확보를위한조례.pdf": "광명시 성인문해교육의 공공성 확보를 위한 조례",
    "광명시신중년층인생이모작지원에관한조례.pdf": "광명시 신중년층 인생이모작 지원에 관한 조례",
}

extracted = (ROOT / "data/regulations/_extracted.txt").read_text(encoding="utf-8")

# Split into per-file sections
raw_sections = re.split(r"={60,}\n", extracted)

articles = []  # list of (law_name, article_header, full_content)

for section in raw_sections:
    section = section.strip()
    if not section:
        continue

    m = re.match(r"FILE:\s+(.+?\.pdf)\n(.*)", section, re.DOTALL)
    if not m:
        continue

    filename = m.group(1).strip()
    content = m.group(2)
    law_name = LAW_NAMES.get(filename)
    if not law_name:
        continue

    # ── Clean page artifacts ──────────────────────────────────────────
    # Remove "--- Page N ---" markers
    content = re.sub(r"--- Page \d+ ---\n?", "", content)
    # Remove page numbers like "- 1 -" or "- 2031 -"
    content = re.sub(r"\n- \d+ -\n", "\n", content)
    # Remove "(추N)" markers
    content = re.sub(r"\n?\(추\d+\)\n?", "\n", content)
    # Remove the compact law-name repetitions (header lines with no spaces)
    compact = filename.replace(".pdf", "")
    content = re.sub(rf"^{re.escape(compact)}\s*\n", "", content, flags=re.MULTILINE)

    # ── Truncate at non-legislative content ───────────────────────────
    # 시행규칙: cut forms off at [별지제1호서식]
    if "시행규칙" in filename:
        idx = content.find("[별지제1호서식]")
        if idx > 0:
            content = content[:idx]

    # 신중년층: cut tables/forms at 【별표1】
    if "신중년층" in filename:
        idx = content.find("【별표1】")
        if idx > 0:
            content = content[:idx]

    # ── Split on article headers ───────────────────────────────────────
    # Matches e.g. 제1조(목적)  /  제17조의2(책무)
    ARTICLE_RE = re.compile(r"(제\d+조(?:의\d+)?\([^)]+\))")
    parts = ARTICLE_RE.split(content)

    i = 1
    while i < len(parts):
        header = parts[i].strip()           # e.g. 제1조(목적)
        body = parts[i + 1] if i + 1 < len(parts) else ""

        # Cut body before 부칙
        for cutoff in ["부칙", "부  칙"]:
            ci = body.find(cutoff)
            if ci >= 0:
                body = body[:ci]

        # Normalize whitespace in body
        body = re.sub(r"\n+", " ", body).strip()
        body = re.sub(r"  +", " ", body)

        full_text = f"{header} {body}".strip()

        articles.append((law_name, header, full_text))
        i += 2

# ── Write SQL ──────────────────────────────────────────────────────────
def esc(s: str) -> str:
    return s.replace("'", "''")

sql_path = ROOT / "backend/db/migrations/006_regulations_gwangmyeong.sql"

with open(sql_path, "w", encoding="utf-8") as f:
    f.write("-- 광명시 자치법규 시드 데이터\n")
    f.write(f"-- 총 {len(articles)}개 조문\n\n")

    for table in ("regulations", "regulations_fts"):
        ignore = "OR IGNORE " if table == "regulations" else ""
        f.write(f"INSERT {ignore}INTO {table} (law_name, article, content) VALUES\n")
        for i, (law, art, txt) in enumerate(articles):
            sep = "," if i < len(articles) - 1 else ";"
            f.write(f"  ('{esc(law)}', '{esc(art)}', '{esc(txt)}'){sep}\n")
        f.write("\n")

print(f"Written {len(articles)} articles → {sql_path}")
