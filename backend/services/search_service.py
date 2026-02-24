"""검색 서비스 — 키워드(FTS5), 시맨틱, 하이브리드."""

from __future__ import annotations

import json

import structlog

from backend.db.database import get_db

log = structlog.get_logger()


class SearchService:
    """문서 검색 (키워드 + 시맨틱 + 하이브리드)."""

    async def search(
        self,
        query: str,
        mode: str = "keyword",
        limit: int = 20,
    ) -> list[dict]:
        """통합 검색."""
        if mode == "keyword":
            return await self._keyword_search(query, limit)
        elif mode == "semantic":
            return await self._semantic_search(query, limit)
        elif mode == "hybrid":
            kw = await self._keyword_search(query, limit)
            sem = await self._semantic_search(query, limit)
            return self._merge_results(kw, sem)
        else:
            return await self._keyword_search(query, limit)

    async def _keyword_search(self, query: str, limit: int) -> list[dict]:
        """FTS5 키워드 검색."""
        results = []
        fts_query = query.replace('"', '""')

        async with get_db() as db:
            sql = (
                "SELECT path, filename, "
                "snippet(documents_fts, 2, '<mark>', '</mark>', '...', 32) AS snippet, "
                "rank "
                "FROM documents_fts "
                "WHERE documents_fts MATCH ? "
                "ORDER BY rank "
                f"LIMIT {limit}"
            )
            async with db.execute(sql, (fts_query,)) as cursor:
                async for row in cursor:
                    results.append({
                        "path": row["path"],
                        "filename": row["filename"],
                        "snippet": row["snippet"],
                        "score": abs(row["rank"]),
                        "search_mode": "keyword",
                    })
        return results

    async def _semantic_search(self, query: str, limit: int) -> list[dict]:
        """시맨틱 검색 (임베딩 기반 코사인 유사도)."""
        try:
            from backend.ai.client import GptOssClient
            from backend.config import settings

            client = GptOssClient(settings.OLLAMA_BASE_URL)
            query_vec = await client.embed(query)
        except Exception:
            return []

        results = []
        async with get_db() as db:
            async with db.execute(
                "SELECT e.chunk_text, e.vector_json, d.path, d.filename "
                "FROM embeddings e JOIN documents d ON e.doc_id = d.id"
            ) as cursor:
                async for row in cursor:
                    doc_vec = json.loads(row["vector_json"])
                    score = self._cosine_similarity(query_vec, doc_vec)
                    results.append({
                        "path": row["path"],
                        "filename": row["filename"],
                        "snippet": row["chunk_text"][:200],
                        "score": score,
                        "search_mode": "semantic",
                    })

        results.sort(key=lambda r: r["score"], reverse=True)
        return results[:limit]

    async def search_regulations(
        self, query: str, scope: str = "all", limit: int = 20
    ) -> list[dict]:
        """법령 검색 (FTS5)."""
        results = []
        fts_query = query.replace('"', '""')

        async with get_db() as db:
            sql = (
                "SELECT law_name, article, "
                "snippet(regulations_fts, 2, '<mark>', '</mark>', '...', 48) AS snippet, "
                "rank "
                "FROM regulations_fts "
                "WHERE regulations_fts MATCH ? "
                "ORDER BY rank "
                f"LIMIT {limit}"
            )
            async with db.execute(sql, (fts_query,)) as cursor:
                async for row in cursor:
                    results.append({
                        "law_name": row["law_name"],
                        "article": row["article"],
                        "snippet": row["snippet"],
                        "score": abs(row["rank"]),
                    })
        return results

    @staticmethod
    def _merge_results(kw: list[dict], sem: list[dict]) -> list[dict]:
        """키워드 + 시맨틱 결과 병합 (RRF)."""
        scores: dict[str, float] = {}
        paths: dict[str, dict] = {}
        k = 60  # RRF constant

        for i, r in enumerate(kw):
            path = r["path"]
            scores[path] = scores.get(path, 0) + 1 / (k + i)
            paths[path] = r

        for i, r in enumerate(sem):
            path = r["path"]
            scores[path] = scores.get(path, 0) + 1 / (k + i)
            if path not in paths:
                paths[path] = r

        merged = []
        for path in sorted(scores, key=lambda p: scores[p], reverse=True):
            item = paths[path].copy()
            item["score"] = scores[path]
            item["search_mode"] = "hybrid"
            merged.append(item)
        return merged

    @staticmethod
    def _cosine_similarity(a: list[float], b: list[float]) -> float:
        if len(a) != len(b):
            return 0.0
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = sum(x * x for x in a) ** 0.5
        norm_b = sum(x * x for x in b) ** 0.5
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)


search_service = SearchService()
