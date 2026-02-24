"""
Ollama AI 클라이언트.

핵심 설계:
  - 모든 호출에 date.today().year 동적 주입 (하드코딩 금지)
  - task 파라미터로 Reasoning level 자동 설정
  - 스트리밍/단일 응답 모두 지원
  - <think> 태그 파싱 (RULE-12: Qwen3 thinking mode)
  - 모델 오버라이드 per-request 지원
  - Ollama 미응답 시 graceful fallback (템플릿 반환)
"""

from __future__ import annotations

import re
from datetime import date
from typing import AsyncIterator, Literal

import httpx
from openai import AsyncOpenAI

ReasoningLevel = Literal["low", "medium", "high"]

TASK_REASONING: dict[str, ReasoningLevel] = {
    "classify": "low",
    "summarize": "low",
    "incoming_doc": "low",
    "gianmun_body": "medium",
    "meeting_minutes": "medium",
    "complaint_resp": "medium",
    "plan_document": "high",
    "budget_calc": "high",
    "docent_plan": "high",
}

SYSTEM_PROMPT_BASE = """당신은 대한민국 광명시청 공문서 작성 및 지역사회 분석을 지원하는 전문 AI입니다.

[핵심 규칙]
- 현재 연도: {year}년. 이 연도 이전 날짜(예: 2023, 2024, 2025)를 생성하면 절대 안 됩니다.
- 공문서는 「행정업무의 효율적 운영에 관한 규정」을 준수합니다.
- 기관명은 "광명시청"을 사용합니다. "○○시청" 같은 자리표시자는 금지합니다.
- 이 초안은 담당자 검토 후 사용해야 합니다.

[작성 지침]
- 사업 목표는 구체적 수치(KPI)를 포함해야 합니다.
- 예산 항목은 반드시 마크다운 표(| 항목 | 수량 | 단가 | 금액 |)로 작성하고, 산출 근거(단가×수량=금액)를 제시합니다.
- 일정·구성·비교 등 구조화된 데이터는 마크다운 표로 작성합니다.
- 사업기간과 추진일정의 시점이 일치해야 합니다 (예: 사업기간이 7월~이면 일정도 7월부터).
- 법령·규정은 정확한 조문 번호를 알 때만 인용하고, 불확실한 경우 조문 번호 없이 법령명만 언급합니다.
- 기대효과에는 반드시 정량적 근거를 제시합니다 (예: "경제효과 150억 원" → 산출 논리 포함).

[서식 규칙]
- 마크다운 문법을 사용합니다: ## 제목, **굵게**, | 표 |, - 목록
- HTML 태그(<br> 등)는 사용하지 않습니다.
- 백틱(`)은 사용하지 않습니다.

Reasoning: {reasoning}
"""

_THINK_RE = re.compile(r"<think>(.*?)</think>", re.DOTALL)


class GptOssClient:
    def __init__(self, base_url: str, model: str = "gpt-oss:20b"):
        self._client = AsyncOpenAI(base_url=f"{base_url}/v1", api_key="ollama")
        self.model = model
        self.base_url = base_url

    async def is_available(self) -> bool:
        """Ollama 서버 접속 가능 여부."""
        try:
            async with httpx.AsyncClient(timeout=5) as c:
                r = await c.get(f"{self.base_url}/api/tags")
                return bool(r.json().get("models"))
        except Exception:
            return False

    # ── Chat (single response) ───────────────────────────────

    async def chat(
        self,
        messages: list[dict],
        task: str = "gianmun_body",
        system_extra: str = "",
        temperature: float = 0.1,
        max_tokens: int = 4096,
        model: str | None = None,
    ) -> dict:
        """단일 응답. Returns {'content': str, 'thinking': str|None, 'model': str}."""
        actual_model = model or self.model
        reasoning = TASK_REASONING.get(task, "medium")
        system = SYSTEM_PROMPT_BASE.format(
            year=date.today().year, reasoning=reasoning
        ) + system_extra

        try:
            resp = await self._client.chat.completions.create(
                model=actual_model,
                messages=[{"role": "system", "content": system}, *messages],
                temperature=temperature,
                max_tokens=max_tokens,
            )
            raw = resp.choices[0].message.content
            thinking, content = self._parse_thinking(raw)
            return {"content": content, "thinking": thinking, "model": actual_model}
        except Exception as e:
            return {
                "content": self._fallback_template(task, e),
                "thinking": None,
                "model": actual_model,
            }

    # ── Stream ───────────────────────────────────────────────

    async def stream(
        self,
        messages: list[dict],
        task: str = "gianmun_body",
        system_extra: str = "",
        model: str | None = None,
    ) -> AsyncIterator[dict]:
        """스트리밍. Yields {'type': 'thinking'|'token', 'content': str}."""
        actual_model = model or self.model
        reasoning = TASK_REASONING.get(task, "medium")
        system = SYSTEM_PROMPT_BASE.format(
            year=date.today().year, reasoning=reasoning
        ) + system_extra

        try:
            raw_stream = await self._client.chat.completions.create(
                model=actual_model,
                messages=[{"role": "system", "content": system}, *messages],
                stream=True,
                max_tokens=4096,
            )

            buf = ""
            in_think = False

            async for chunk in raw_stream:
                tok = chunk.choices[0].delta.content
                if not tok:
                    continue
                buf += tok

                # Process buffer for <think>...</think> tags
                while True:
                    if in_think:
                        end = buf.find("</think>")
                        if end >= 0:
                            if end > 0:
                                yield {"type": "thinking", "content": buf[:end]}
                            buf = buf[end + 8:]
                            in_think = False
                            continue
                        # Partial tag guard: keep last 8 chars
                        safe = max(0, len(buf) - 8)
                        if safe > 0:
                            yield {"type": "thinking", "content": buf[:safe]}
                            buf = buf[safe:]
                        break
                    else:
                        start = buf.find("<think>")
                        if start >= 0:
                            if start > 0:
                                yield {"type": "token", "content": buf[:start]}
                            buf = buf[start + 7:]
                            in_think = True
                            continue
                        # Partial tag guard: keep last 7 chars
                        safe = max(0, len(buf) - 7)
                        if safe > 0:
                            yield {"type": "token", "content": buf[:safe]}
                            buf = buf[safe:]
                        break

            # Flush remaining buffer
            if buf.strip():
                yield {"type": "thinking" if in_think else "token", "content": buf}

        except Exception as e:
            yield {"type": "token", "content": self._fallback_template(task, e)}

    # ── Embed ────────────────────────────────────────────────

    async def embed(self, text: str) -> list[float]:
        async with httpx.AsyncClient(timeout=30) as c:
            r = await c.post(
                f"{self.base_url}/api/embeddings",
                json={"model": "nomic-embed-text", "prompt": text},
            )
            return r.json()["embedding"]

    # ── Helpers ──────────────────────────────────────────────

    @staticmethod
    def _parse_thinking(text: str) -> tuple[str | None, str]:
        """<think>...</think> 파싱. Returns (thinking, content)."""
        m = _THINK_RE.search(text)
        if m:
            thinking = m.group(1).strip()
            content = (text[: m.start()] + text[m.end() :]).strip()
            return thinking, content
        return None, text

    def _fallback_template(self, task: str, error: Exception) -> str:
        year = date.today().year
        return (
            f"[AI 서버 연결 실패: {type(error).__name__}]\n\n"
            f"아래 항목을 직접 작성하십시오 ({year}년 기준):\n\n"
            "1. [작성필요] 사업 목적\n"
            "2. [작성필요] 추진 내용\n"
            "3. [작성필요] 소요 예산\n"
            "4. [작성필요] 기대 효과\n"
        )
