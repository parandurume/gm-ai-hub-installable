"""문서 관련 Pydantic 모델."""

from __future__ import annotations

from pydantic import BaseModel, Field


class DocumentMetadata(BaseModel):
    """문서 메타데이터."""

    id: int | None = None
    path: str
    filename: str
    ext: str
    size_bytes: int | None = None
    text_hash: str | None = None
    indexed_at: str | None = None
    title: str | None = None
    author: str | None = None
    created: str | None = None


class SearchResult(BaseModel):
    """검색 결과 항목."""

    path: str
    filename: str
    snippet: str = ""
    score: float = 0.0
    search_mode: str = "keyword"


class DocumentCreateRequest(BaseModel):
    """문서 생성 요청."""

    template: str = Field(..., description="템플릿 이름 (예: 일반기안)")
    fields: dict[str, str] = Field(default_factory=dict, description="필드 값")
    output_path: str | None = Field(None, description="출력 경로")


class DocumentEditRequest(BaseModel):
    """문서 편집 요청."""

    operation: str = Field(..., description="append | replace")
    text: str = Field(..., description="추가/교체 텍스트")
    search: str | None = Field(None, description="replace 시 찾을 텍스트")


class DraftRequest(BaseModel):
    """공문서 초안 생성 요청."""

    doc_type: str = Field("일반기안", description="문서 종류")
    subject: str = Field(..., description="제목")
    recipients: str = Field("", description="수신처")
    body_text: str = Field("", description="본문 (직접 입력)")
    ai_instruction: str = Field("", description="AI 본문 생성 지시")
    attachments: str = Field("", description="첨부")
    output_path: str | None = None


class MeetingRequest(BaseModel):
    """회의록 생성 요청."""

    title: str
    meeting_date: str = Field("", alias="date", serialization_alias="meeting_date")
    attendees: str
    content: str
    model: str | None = None
    location: str = ""
    decisions: str = ""
    action_items: str = ""
    output_path: str | None = None

    model_config = {"populate_by_name": True}


class ComplaintRequest(BaseModel):
    """민원 답변 요청."""

    complaint_text: str
    complaint_type: str | None = None
    response_body: str | None = None
    output_path: str | None = None


class PiiScanRequest(BaseModel):
    """PII 스캔 요청."""

    path: str
    pii_types: list[str] | None = None
    action: str = Field("report", description="report | mask | redact")


class DiffRequest(BaseModel):
    """문서 비교 요청."""

    path_a: str
    path_b: str


class AiBodyRequest(BaseModel):
    """AI 본문 생성 요청."""

    instruction: str
    doc_type: str = "일반기안"
    subject: str = ""
    model: str | None = None


class DraftSaveRequest(BaseModel):
    """공문서 초안 HWPX 저장 요청."""

    doc_type: str = "일반기안"
    subject: str
    body: str
    recipients: str = ""
    output_path: str | None = None


class DraftValidateRequest(BaseModel):
    """공문서 초안 텍스트 검증 요청."""

    text: str = Field(..., description="검증할 텍스트")


class Annotation(BaseModel):
    """인라인 검증 어노테이션."""

    type: str = Field(..., description="date | pii | budget")
    subtype: str = Field("", description="세부 유형 (예: 주민등록번호)")
    start: int = Field(..., description="시작 오프셋")
    end: int = Field(..., description="종료 오프셋")
    severity: str = Field("warning", description="info | warning | error")
    message: str = Field("", description="설명 메시지")


class PiiScanBody(BaseModel):
    """PII 스캔 요청 본문."""

    path: str
    pii_types: list[str] | None = None
    include_text: bool = Field(False, description="응답에 원문/마스킹 텍스트 포함")


class PiiBatchScanBody(BaseModel):
    """PII 배치 스캔 요청."""

    paths: list[str]
    pii_types: list[str] | None = None


class TaskOrderRequest(BaseModel):
    """과업지시서 AI 생성 요청."""

    task_name: str = Field(..., description="과업명")
    purpose: str = Field("", description="과업목적")
    period: str = Field("", description="과업기간 (예: 착수일로부터 2026. 12. 31.까지)")
    location: str = Field("", description="과업장소")
    budget: str = Field("", description="소요예산 (예: 금20,000천원)")
    scope_items: list[str] = Field(default_factory=list, description="과업범위 항목")
    details: str = Field("", description="추가 지시사항 / 세부내용")
    model: str | None = None


class TaskOrderSaveRequest(BaseModel):
    """과업지시서 HWPX 저장 요청."""

    task_name: str = Field(..., description="과업명")
    body: str = Field(..., description="AI 생성 본문")
    output_path: str | None = None


class ChatMessage(BaseModel):
    """채팅 메시지."""

    content: str
    model: str | None = None
    reasoning: str = "medium"
    context: list[dict] = Field(default_factory=list)
