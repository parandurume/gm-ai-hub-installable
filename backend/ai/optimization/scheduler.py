"""주기적 MIPROv2 재최적화 스케줄러."""

from __future__ import annotations

from datetime import date

from backend.db.database import get_db

OPTIMIZATION_SCHEDULE = {
    "draft": {"min_new_docs": 20, "max_interval_days": 30},
    "docent": {"min_new_docs": 5, "max_interval_days": 90},
    "complaint": {"min_new_docs": 30, "max_interval_days": 14},
    "meeting": {"min_new_docs": 10, "max_interval_days": 60},
}


async def check_optimization_needed(pipeline_name: str) -> dict:
    """재최적화 필요 여부 판단."""
    async with get_db() as db:
        async with db.execute(
            "SELECT last_optimized_at, doc_count_at_optimization "
            "FROM optimization_history WHERE pipeline = ? "
            "ORDER BY last_optimized_at DESC LIMIT 1",
            (pipeline_name,),
        ) as cursor:
            row = await cursor.fetchone()

        async with db.execute(
            "SELECT COUNT(*) as cnt FROM audit_log "
            "WHERE action LIKE ? AND success = 1",
            (f"%{pipeline_name}%",),
        ) as cursor:
            count_row = await cursor.fetchone()
            current_count = count_row["cnt"] if count_row else 0

    schedule = OPTIMIZATION_SCHEDULE.get(pipeline_name, {})

    if not row:
        return {
            "needed": True,
            "reason": "최초 최적화 필요",
            "new_doc_count": current_count,
        }

    last_opt = row["last_optimized_at"]
    doc_at_opt = row["doc_count_at_optimization"]
    new_docs = current_count - (doc_at_opt or 0)

    # 간격 초과
    max_days = schedule.get("max_interval_days", 30)
    if (date.today() - date.fromisoformat(last_opt[:10])).days > max_days:
        return {
            "needed": True,
            "reason": "최적화 간격 초과",
            "new_doc_count": new_docs,
        }

    # 새 문서 충분
    if new_docs >= schedule.get("min_new_docs", 20):
        return {
            "needed": True,
            "reason": f"새 문서 {new_docs}개 축적",
            "new_doc_count": new_docs,
        }

    return {
        "needed": False,
        "reason": "최적화 불필요",
        "new_doc_count": new_docs,
        "last_optimized": last_opt,
    }
