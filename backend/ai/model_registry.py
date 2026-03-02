"""모델 레지스트리 — 동적 모델 감지 및 태스크별 자동 선택 (RULE-11)."""

from __future__ import annotations

import httpx

from backend.ai.model_profiles import (
    BUILTIN_PROFILES,
    VISION_FAMILIES,
    ModelProfile,
    detect_family,
    extract_param_size,
)

ENVIRONMENT_DEFAULTS: dict[str, dict[str, str]] = {
    "govpc": {
        "default": "gpt-oss:20b",
        "classify": "exaone3.5:7.8b",
        "summarize": "exaone3.5:7.8b",
        "draft_body": "gpt-oss:20b",
        "plan_document": "gpt-oss:20b",
        "budget_calc": "gpt-oss:20b",
        "docent_plan": "gpt-oss:20b",
    },
    "laptop": {
        "default": "qwen3:14b",
        "classify": "qwen3:8b",
        "summarize": "qwen3:8b",
        "draft_body": "qwen3:14b",
        "plan_document": "qwen3:14b",
        "budget_calc": "qwen3:14b",
        "docent_plan": "qwen3:14b",
        "complaint_resp": "qwen3:14b",
    },
    "desktop": {
        "default": "qwen3:14b",
        "classify": "joonoh/HyperCLOVAX-SEED-Text-Instruct-1.5B",
        "summarize": "joonoh/HyperCLOVAX-SEED-Text-Instruct-1.5B",
        "draft_body": "qwen3:14b",
        "plan_document": "qwen3:14b",
        "budget_calc": "qwen3:14b",
        "docent_plan": "qwen3:14b",
        "complaint_resp": "qwen3:14b",
        "meeting_minutes": "qwen3:14b",
        "incoming_doc": "joonoh/HyperCLOVAX-SEED-Text-Instruct-1.5B",
    },
}


class ModelRegistry:
    """Ollama 모델 동적 감지 + 태스크별 최적 모델 선택 (패밀리 기반)."""

    def __init__(self, ollama_url: str):
        self._url = ollama_url
        self._available: list[ModelProfile] = []
        self._profiles: dict[str, ModelProfile] = dict(BUILTIN_PROFILES)

    # ── Refresh ──────────────────────────────────────────────

    async def refresh(self) -> list[str]:
        """Ollama에서 현재 설치된 모델 목록 조회 (패밀리 매칭)."""
        try:
            async with httpx.AsyncClient(timeout=10) as c:
                r = await c.get(f"{self._url}/api/tags")
                models = r.json().get("models", [])

            self._available = []
            for m in models:
                name = m["name"]
                # 1) Exact match in builtin profiles
                if name in self._profiles:
                    self._available.append(self._profiles[name])
                    continue
                # 2) Family match → create profile from best builtin sibling
                profile = self._match_by_family(name)
                if profile:
                    self._available.append(profile)
                    self._profiles[name] = profile
                    continue
                # 3) No match → auto-detect from ollama data
                profile = ModelProfile.from_ollama(m)
                self._available.append(profile)
                self._profiles[name] = profile

            return [m.id for m in self._available]
        except Exception:
            return []

    # ── Select ───────────────────────────────────────────────

    def select(
        self,
        task: str,
        env: str,
        user_override: str | None = None,
        reasoning: str = "medium",
    ) -> tuple[str, bool]:
        """태스크에 맞는 모델 선택. Returns: (model_id, use_thinking)."""
        # 1. 사용자 명시 오버라이드
        if user_override:
            resolved = self._resolve(user_override)
            if resolved:
                profile = self._profiles.get(resolved)
                thinking = self._should_think(profile, reasoning)
                return resolved, thinking

        # 2. 환경별 태스크 매핑
        env_map = ENVIRONMENT_DEFAULTS.get(env, ENVIRONMENT_DEFAULTS["govpc"])
        candidate = env_map.get(task, env_map["default"])

        # 3. 설치 여부 확인 → fallback
        resolved = self._resolve(candidate)
        if not resolved:
            resolved = self._fallback()

        profile = self._profiles.get(resolved)
        thinking = self._should_think(profile, reasoning)
        return resolved, thinking

    # ── Public getters ───────────────────────────────────────

    def get_available_models(self) -> list[dict]:
        """설치된 모델 + 미설치 빌트인 프로파일 목록."""
        seen_ids: set[str] = set()
        seen_families: set[str] = set()
        result: list[dict] = []

        # Installed models first
        for m in self._available:
            info = m.to_dict()
            info["available"] = True
            result.append(info)
            seen_ids.add(m.id)
            seen_families.add(m.family)

        # Uninstalled builtins (skip if family already covered)
        for profile in BUILTIN_PROFILES.values():
            if profile.id not in seen_ids and profile.family not in seen_families:
                info = profile.to_dict()
                info["available"] = False
                info["install_command"] = f"ollama pull {profile.id}"
                result.append(info)

        return result

    def select_vision(self) -> str | None:
        """설치된 비전 모델 중 가장 큰 것을 반환 (없으면 None)."""
        candidates = [m for m in self._available if m.supports_vision]
        if not candidates:
            return None
        candidates.sort(key=lambda x: x.param_size, reverse=True)
        return candidates[0].id

    def get_profile(self, model_id: str) -> ModelProfile | None:
        """ID로 프로파일 조회."""
        return self._profiles.get(model_id)

    # ── Internal helpers ─────────────────────────────────────

    def _match_by_family(self, model_name: str) -> ModelProfile | None:
        """패밀리 기반으로 빌트인 프로파일에서 매칭하여 새 프로파일 생성."""
        family, thinking = detect_family(model_name)
        if family == "unknown":
            return None

        # Find best builtin sibling for strengths/best_for inheritance
        sibling = None
        for p in BUILTIN_PROFILES.values():
            if p.family == family:
                sibling = p
                break

        param = extract_param_size(model_name) or (sibling.param_size if sibling else 0)
        return ModelProfile(
            id=model_name,
            name=model_name,
            family=family,
            param_size=param,
            ram_gb=max(4, param) if param else (sibling.ram_gb if sibling else 8),
            supports_thinking=thinking,
            supports_embedding=sibling.supports_embedding if sibling else False,
            supports_vision=family in VISION_FAMILIES,
            context_len=sibling.context_len if sibling else 32768,
            strengths=sibling.strengths if sibling else [],
            best_for=sibling.best_for if sibling else [],
        )

    def _resolve(self, model_id: str) -> str | None:
        """모델 ID를 설치된 실제 모델 ID로 해석 (exact → family)."""
        # Exact match
        for m in self._available:
            if m.id == model_id:
                return model_id

        # Family match — prefer largest param size
        family, _ = detect_family(model_id)
        if family != "unknown":
            candidates = [m for m in self._available if m.family == family]
            if candidates:
                candidates.sort(key=lambda x: x.param_size, reverse=True)
                return candidates[0].id

        return None

    def _fallback(self) -> str:
        """설치된 모델 중 가장 적합한 것으로 대체 (패밀리 기반)."""
        preferred_families = [
            "gpt-oss", "qwen3", "qwen3.5", "exaone",
            "hyperclovax", "deepseek-r1", "phi4", "llama3.2", "llama3",
        ]
        for fam in preferred_families:
            candidates = [m for m in self._available if m.family == fam]
            if candidates:
                candidates.sort(key=lambda x: x.param_size, reverse=True)
                return candidates[0].id

        # Skip embedding-only models as generative fallback
        generative = [m for m in self._available if not m.supports_embedding]
        return generative[0].id if generative else "qwen3:8b"

    @staticmethod
    def _should_think(profile: ModelProfile | None, reasoning: str) -> bool:
        return (
            reasoning == "high"
            and profile is not None
            and profile.supports_thinking
        )
