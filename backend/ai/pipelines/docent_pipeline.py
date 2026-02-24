"""
AI 도슨트 육성사업 계획서 생성 파이프라인.

gpt-oss:20b Reasoning: high 사용.
DSPy Assert로 날짜·예산 3중 검증 (RULE-02: 최소 4개 Assert).
"""

from __future__ import annotations

from datetime import date

import dspy

from backend.ai.guards import BudgetValidator, DateGuard
from backend.ai.signatures.docent_sigs import (
    ClassifyDocentProject,
    GenerateDocentBackground,
    GenerateDocentImplementation,
    ReasonDocentBudget,
)


class AiDocentPlanPipeline(dspy.Module):
    def __init__(self):
        self.classify = dspy.ChainOfThought(ClassifyDocentProject)
        self.budget = dspy.ChainOfThought(ReasonDocentBudget)
        self.background = dspy.ChainOfThought(GenerateDocentBackground)
        self.implement = dspy.ChainOfThought(GenerateDocentImplementation)

    def forward(
        self,
        user_request: str,
        target_count: int,
        duration_months: int,
        rag_contexts: dict | None = None,
        current_year: int | None = None,
    ):
        YEAR = current_year or date.today().year  # 동적 (RULE-01)
        ctx = rag_contexts or {}

        # 1. 분류 (Reasoning: low)
        cls = self.classify(
            user_request=user_request,
            current_year=YEAR,
            reference_projects=ctx.get("reference", ""),
        )

        # 2. 예산 (Reasoning: high)
        bud = self.budget(
            project_title=user_request,
            target_count=target_count,
            duration_months=duration_months,
            current_year=YEAR,
            budget_guidelines=ctx.get("budget", ""),
        )

        # ── Assert 1: 회계연도 ──────────────────────────────────
        dspy.Assert(
            int(bud.fiscal_year) >= YEAR,
            f"회계연도 오류({bud.fiscal_year}). {YEAR}년 이상 필요.",
        )
        # ── Assert 2: 예산 총액 ─────────────────────────────────
        dspy.Assert(
            int(bud.total_krw) > 0,
            "예산 총액이 0입니다. 사업 규모에 맞는 예산을 산출하십시오.",
        )
        # ── Assert 3: 항목 수 ───────────────────────────────────
        items = bud.items if isinstance(bud.items, list) else []
        dspy.Assert(
            len(items) >= 3,
            "예산 항목이 3개 미만입니다 (인건비·운영비·교육비 이상 필요).",
        )

        # 3. 배경 (Reasoning: medium)
        bg = self.background(
            project_title=user_request,
            current_year=YEAR,
            gwangmyeong_context=ctx.get("gwangmyeong", ""),
            ai_trend_context=ctx.get("ai_trend", ""),
        )

        # ── Assert 4: 배경 연도 ────────────────────────────────
        bg_paras = bg.background_paragraphs
        if isinstance(bg_paras, list):
            bg_text = " ".join(str(p) for p in bg_paras)
        else:
            bg_text = str(bg_paras)

        date_scan = DateGuard.scan(bg_text)
        dspy.Assert(
            date_scan["passed"],
            f"배경 본문에 구식 연도: {date_scan['stale_years']}. {YEAR}년 이상만 허용.",
        )

        # 4. 추진 계획 (Reasoning: high)
        impl = self.implement(
            project_title=user_request,
            target_count=target_count,
            budget_total=int(bud.total_krw),
            background=bg_paras if isinstance(bg_paras, list) else [bg_text],
            current_year=YEAR,
        )

        return dspy.Prediction(
            classification=cls,
            budget=bud,
            background=bg,
            implementation=impl,
            generated_year=YEAR,
        )
