"""법제처 Open API 서비스 — law.go.kr 법령 검색."""

from __future__ import annotations

import os

import httpx
import structlog
from dotenv import dotenv_values

from backend import paths
from backend.db.database import get_setting

log = structlog.get_logger()

# 법령 목록 검색
LAW_SEARCH_URL = "http://www.law.go.kr/DRF/lawSearch.do"
# 법령 본문 상세 조회
LAW_SERVICE_URL = "http://www.law.go.kr/DRF/lawService.do"
_TIMEOUT = 10

# 세션 OC — 메모리에만 저장, 앱 종료 시 소멸
_session_oc: str = ""


class LawApiUnavailable(Exception):
    """법제처 API를 사용할 수 없을 때."""


def _read_oc_from_env() -> str:
    """LAW_API_OC를 .env 파일 또는 환경변수에서 읽기."""
    from pathlib import Path

    # 1) 시스템 환경변수
    oc = os.environ.get("LAW_API_OC", "")
    if oc:
        return oc
    # 2) %LOCALAPPDATA%/GM-AI-Hub/.env (설치 환경)
    for env_path in [paths.env_file_path(), Path(".env")]:
        if env_path.exists():
            values = dotenv_values(env_path)
            oc = values.get("LAW_API_OC", "")
            if oc:
                return oc
    return ""


def set_session_oc(oc: str) -> None:
    """세션 OC 설정 (메모리에만 저장)."""
    global _session_oc
    _session_oc = oc.strip()


def get_session_oc() -> str:
    """현재 세션 OC 반환."""
    return _session_oc


class LawApiService:
    """법제처 Open API 클라이언트."""

    async def _get_oc(self) -> str:
        """OC 키 조회: 세션 → .env → DB 순."""
        if _session_oc:
            return _session_oc
        env_oc = _read_oc_from_env()
        if env_oc:
            return env_oc
        return await get_setting("law_api_key", "")

    async def is_available(self) -> bool:
        """API key 존재 + 인터넷 연결 확인."""
        oc = await self._get_oc()
        if not oc:
            return False
        try:
            async with httpx.AsyncClient(timeout=3) as client:
                r = await client.get(
                    LAW_SEARCH_URL,
                    params={"OC": oc, "target": "law", "type": "JSON", "query": "법"},
                )
                if r.status_code != 200:
                    return False
                data = r.json()
                # API 오류 응답 체크 (사용자/IP 검증 실패 등)
                if "result" in data and "실패" in data.get("result", ""):
                    return False
                return True
        except Exception:
            return False

    async def search(self, query: str, limit: int = 20) -> list[dict]:
        """법제처 API로 법령 검색. 실패 시 LawApiUnavailable 발생."""
        oc = await self._get_oc()
        if not oc:
            raise LawApiUnavailable("API 키 미설정")

        try:
            async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
                r = await client.get(
                    LAW_SEARCH_URL,
                    params={
                        "OC": oc,
                        "target": "law",
                        "type": "JSON",
                        "query": query,
                    },
                )
                r.raise_for_status()
                data = r.json()
        except httpx.HTTPError as exc:
            log.warning("법제처 API 요청 실패", error=str(exc))
            raise LawApiUnavailable(f"API 요청 실패: {exc}") from exc
        except Exception as exc:
            log.warning("법제처 API 파싱 실패", error=str(exc))
            raise LawApiUnavailable(f"응답 처리 실패: {exc}") from exc

        # API 오류 응답 체크
        if "result" in data and "실패" in data.get("result", ""):
            msg = data.get("msg", data["result"])
            raise LawApiUnavailable(msg)

        results: list[dict] = []
        laws = data.get("LawSearch", {}).get("law", [])
        if isinstance(laws, dict):
            laws = [laws]

        for item in laws[:limit]:
            law_name = item.get("법령명한글", "") or item.get("lawNameKorean", "")
            law_id = item.get("법령일련번호", "") or item.get("lawId", "")
            abbrev = item.get("법령약칭", "") or item.get("lawAbbreviation", "")
            enforce_date = item.get("시행일자", "") or item.get("enforcementDate", "")
            results.append({
                "law_name": law_name,
                "law_id": law_id,
                "article": "",
                "content": abbrev or law_name,
                "snippet": f"{law_name} (시행 {enforce_date})" if enforce_date else law_name,
                "score": 1.0,
                "source": "online",
            })

        return results


law_api_service = LawApiService()
