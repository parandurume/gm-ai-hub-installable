"""회의록 정리 파이프라인."""

from __future__ import annotations

from datetime import date

import dspy

from backend.ai.signatures.document_sigs import SummarizeMeeting


class MeetingSummaryPipeline(dspy.Module):
    def __init__(self):
        self.summarize = dspy.ChainOfThought(SummarizeMeeting)

    def forward(
        self,
        raw_content: str,
        attendees: str,
        current_year: int | None = None,
    ):
        YEAR = current_year or date.today().year

        result = self.summarize(
            raw_content=raw_content,
            attendees=attendees,
            current_year=YEAR,
        )

        return dspy.Prediction(
            summary=result.summary,
            decisions=result.decisions,
            action_items=result.action_items,
            generated_year=YEAR,
        )
