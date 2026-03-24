"""과업지시서 생성 파이프라인."""

from __future__ import annotations

from datetime import date

import dspy

from backend.ai.guards import DateGuard
from backend.ai.signatures.document_sigs import GenerateTaskOrder


class TaskOrderPipeline(dspy.Module):
    def __init__(self):
        self.generate = dspy.ChainOfThought(GenerateTaskOrder)

    def forward(
        self,
        task_name: str,
        purpose: str = "",
        period: str = "",
        location: str = "",
        budget: str = "",
        scope_items: str = "",
        details: str = "",
        current_year: int | None = None,
    ):
        YEAR = current_year or date.today().year

        result = self.generate(
            task_name=task_name,
            purpose=purpose,
            period=period,
            location=location,
            budget=budget,
            scope_items=scope_items,
            details=details,
            current_year=YEAR,
        )

        # DateGuard 검증
        body = result.body if isinstance(result.body, str) else str(result.body)
        scan = DateGuard.scan(body)
        if not scan["passed"]:
            body = DateGuard.fix(body)

        return dspy.Prediction(
            body=body,
            generated_year=YEAR,
        )
