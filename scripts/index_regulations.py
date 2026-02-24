"""법령 데이터 인덱싱 스크립트

data/regulations/ 폴더의 JSON/TXT 법령 파일을 DB에 인덱싱합니다.
"""

import asyncio
import json
import sys
from pathlib import Path

# 프로젝트 루트를 path에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from backend.config import settings
from backend.db.database import init_db, get_db


async def index_regulations():
    """법령 파일을 DB regulations 테이블에 인덱싱"""
    reg_dir = Path(settings.DATA_DIR) / "regulations"
    if not reg_dir.exists():
        print(f"법령 디렉토리가 없습니다: {reg_dir}")
        print("data/regulations/ 폴더에 법령 파일을 넣어주세요.")
        return

    await init_db()

    files = list(reg_dir.glob("*.json")) + list(reg_dir.glob("*.txt"))
    if not files:
        print("인덱싱할 법령 파일이 없습니다.")
        return

    count = 0
    async with get_db() as db:
        for f in files:
            try:
                if f.suffix == ".json":
                    data = json.loads(f.read_text(encoding="utf-8"))
                    if isinstance(data, list):
                        for item in data:
                            await _insert_regulation(db, item)
                            count += 1
                    else:
                        await _insert_regulation(db, data)
                        count += 1
                else:
                    # TXT 파일: 파일명을 법령명으로 사용
                    content = f.read_text(encoding="utf-8")
                    await _insert_regulation(db, {
                        "title": f.stem,
                        "content": content,
                    })
                    count += 1
            except Exception as e:
                print(f"  오류: {f.name} - {e}")

        await db.commit()

    print(f"\n완료: {count}건 인덱싱됨")


async def _insert_regulation(db, item: dict):
    """단일 법령 레코드 삽입 (upsert)"""
    title = item.get("title", item.get("law_name", ""))
    content = item.get("content", item.get("text", ""))
    article = item.get("article", "")
    category = item.get("category", "")

    if not title or not content:
        return

    await db.execute(
        """INSERT OR REPLACE INTO regulations (title, article, content, category)
           VALUES (?, ?, ?, ?)""",
        (title, article, content, category),
    )
    print(f"  + {title} {article}")


if __name__ == "__main__":
    asyncio.run(index_regulations())
