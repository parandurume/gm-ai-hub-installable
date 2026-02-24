"""기안문 본문 생성 파이프라인."""

from __future__ import annotations

from datetime import date

import dspy

from backend.ai.guards import DateGuard
from backend.ai.signatures.document_sigs import GenerateGianmunBody


class GianmunBodyPipeline(dspy.Module):
    def __init__(self):
        self.generate = dspy.ChainOfThought(GenerateGianmunBody)

    def forward(
        self,
        user_request: str,
        doc_type: str = "일반기안",
        recipients: str = "",
        current_year: int | None = None,
    ):
        YEAR = current_year or date.today().year

        result = self.generate(
            user_request=user_request,
            doc_type=doc_type,
            current_year=YEAR,
            recipients=recipients,
        )

        # DateGuard 검증
        body = result.body if isinstance(result.body, str) else str(result.body)
        scan = DateGuard.scan(body)
        if not scan["passed"]:
            body = DateGuard.fix(body)

        return dspy.Prediction(
            body=body,
            fiscal_year=result.fiscal_year,
            doc_type=doc_type,
            generated_year=YEAR,
        )
