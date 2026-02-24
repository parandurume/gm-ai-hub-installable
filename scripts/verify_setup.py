#!/usr/bin/env python3
"""GM-AI-Hub 설치 검증 스크립트."""

from __future__ import annotations

import sys
from pathlib import Path

# 프로젝트 루트를 sys.path에 추가
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def check(name: str, fn) -> bool:
    try:
        result = fn()
        status = "OK" if result else "WARN"
        icon = "\u2705" if result else "\u26a0\ufe0f"
        print(f"  {icon} {name}: {status}")
        return bool(result)
    except Exception as e:
        print(f"  \u274c {name}: FAIL ({e})")
        return False


def main():
    print("=" * 50)
    print("GM-AI-Hub 설치 검증")
    print("=" * 50)
    results = []

    # 1. Python 버전
    results.append(check(
        f"Python {sys.version_info.major}.{sys.version_info.minor}",
        lambda: sys.version_info >= (3, 11),
    ))

    # 2. 핵심 패키지
    print("\n[핵심 패키지]")
    for pkg in [
        "fastapi", "uvicorn", "pydantic", "pydantic_settings",
        "aiosqlite", "httpx", "structlog", "lxml",
    ]:
        results.append(check(pkg, lambda p=pkg: __import__(p)))

    # 3. 선택 패키지
    print("\n[선택 패키지]")
    for pkg in ["watchdog", "dspy", "openai"]:
        check(pkg, lambda p=pkg: __import__(p))

    # 4. 설정 로드
    print("\n[설정]")
    results.append(check("backend.config", lambda: __import__("backend.config")))

    # 5. .env 파일
    env_file = ROOT / ".env"
    results.append(check(
        ".env 파일", lambda: env_file.exists() or (ROOT / ".env.example").exists()
    ))

    # 6. DB 마이그레이션 파일
    print("\n[데이터베이스]")
    results.append(check(
        "001_initial.sql",
        lambda: (ROOT / "backend/db/migrations/001_initial.sql").exists(),
    ))
    results.append(check(
        "002_models_and_optimization.sql",
        lambda: (ROOT / "backend/db/migrations/002_models_and_optimization.sql").exists(),
    ))

    # 7. 템플릿 디렉토리
    print("\n[템플릿]")
    check(
        "data/templates 디렉토리",
        lambda: (ROOT / "data/templates").exists(),
    )

    # 8. Ollama 연결
    print("\n[Ollama]")
    try:
        import httpx as _httpx
        from backend.config import settings

        r = _httpx.get(f"{settings.OLLAMA_BASE_URL}/api/tags", timeout=5)
        models = [m["name"] for m in r.json().get("models", [])]
        check("Ollama 연결", lambda: True)
        for m in models:
            print(f"    \U0001f4e6 {m}")
    except Exception:
        check("Ollama 연결", lambda: False)

    # 9. HWPX 서비스
    print("\n[HWPX]")
    results.append(check(
        "HwpxService import",
        lambda: __import__("backend.services.hwpx_service"),
    ))

    # 결과 요약
    passed = sum(results)
    total = len(results)
    print(f"\n{'=' * 50}")
    print(f"결과: {passed}/{total} 통과")
    if passed == total:
        print("\u2705 모든 검증 통과!")
    else:
        print("\u26a0\ufe0f 일부 항목 확인 필요")
    print("=" * 50)

    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
