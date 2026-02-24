"""민원 답변 파이프라인."""

from __future__ import annotations

from datetime import date

import dspy

from backend.ai.guards import DateGuard
from backend.ai.signatures.document_sigs import DraftComplaintResponse


class ComplaintDraftPipeline(dspy.Module):
    def __init__(self):
        self.draft = dspy.ChainOfThought(DraftComplaintResponse)

    def forward(
        self,
        complaint_text: str,
        current_year: int | None = None,
    ):
        YEAR = current_year or date.today().year

        result = self.draft(
            complaint_text=complaint_text,
            current_year=YEAR,
        )

        # DateGuard 검증
        body = result.response_body
        if isinstance(body, str):
            scan = DateGuard.scan(body)
            if not scan["passed"]:
                body = DateGuard.fix(body)

        return dspy.Prediction(
            classification=result.classification,
            response_body=body,
            legal_refs=result.legal_refs,
            generated_year=YEAR,
        )
