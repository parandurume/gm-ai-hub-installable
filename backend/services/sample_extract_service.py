"""HWPX 샘플 문서 → MIPROv2 학습 예시 변환 서비스."""

from __future__ import annotations

import hashlib
import json
from datetime import date
from pathlib import Path

import structlog

from backend.services.hwpx_service import HwpxService

log = structlog.get_logger()

from backend import paths

SAMPLES_ROOT = paths.user_samples_dir()
EXAMPLES_ROOT = paths.user_examples_dir()
VALID_PIPELINES = {"gianmun", "docent", "complaint", "meeting"}

# ── Pipeline-specific AI prompts ──────────────────────────────────

_ANALYSIS_PROMPTS: dict[str, str] = {
    "gianmun": (
        "당신은 대한민국 지방자치단체 공문서 분석 전문가입니다.\n"
        "아래 공문서 본문을 분석하여 **반드시 JSON만** 응답하세요. "
        "설명·인사말·마크다운 코드펜스(```)는 금지입니다.\n\n"
        "[공문서 본문]\n{body}\n\n"
        "추출 필드:\n"
        '- "doc_type": 문서 유형 — 다음 중 택1: '
        "일반기안, 협조전, 보고서, 계획서, 결과보고서, 회의록, 민원답변\n"
        '- "subject": 문서 제목 (1줄, 핵심 키워드 포함)\n'
        '- "instruction": 이 문서를 작성하라고 지시하는 문장 '
        "(1~2문장, 예: '○○ 계획 기안', '○○ 협조 요청 공문 작성')\n\n"
        "JSON 예시:\n"
        '{{"doc_type":"일반기안","subject":"AI 교육 실시 계획",'
        '"instruction":"직원 대상 AI 활용 교육 계획을 기안해 주세요"}}'
    ),
    "docent": (
        "당신은 공문서 분석 전문가입니다.\n"
        "아래 문서에서 교육/사업 계획 정보를 추출하여 **JSON만** 응답하세요.\n\n"
        "[문서 본문]\n{body}\n\n"
        "추출 필드:\n"
        '- "title": 사업/교육명\n'
        '- "target_count": 대상 인원 수 (숫자, 불명확하면 10)\n'
        '- "months": 사업 기간 (개월 수, 불명확하면 6)\n'
        '- "expected_project_type": 교육훈련|시스템구축|장비도입|서비스개발 중 택1\n\n'
        "JSON만 응답하세요."
    ),
    "complaint": (
        "당신은 민원 분석 전문가입니다.\n"
        "아래 민원 답변서를 분석하여 **JSON만** 응답하세요.\n\n"
        "[민원 답변서 본문]\n{body}\n\n"
        "추출 필드:\n"
        '- "expected_category": 민원 유형 (예: 교통/주차, 환경/청소, 복지/보건, 도시/건축, 기타)\n'
        '- "expected_department": 담당 부서명 (불명확하면 빈 문자열)\n'
        '- "expected_urgency": low|medium|high 중 택1\n'
        '- "complaint_summary": 원래 민원 내용 요약 (1~2문장)\n\n'
        "JSON만 응답하세요."
    ),
    "meeting": (
        "당신은 회의록 분석 전문가입니다.\n"
        "아래 회의록을 분석하여 **JSON만** 응답하세요.\n\n"
        "[회의록 본문]\n{body}\n\n"
        "추출 필드:\n"
        '- "title": 회의 제목\n'
        '- "date": 회의 일자 (YYYY-MM-DD, 불명확하면 빈 문자열)\n'
        '- "attendees": 참석자 (쉼표 구분)\n\n'
        "JSON만 응답하세요."
    ),
}


# ── Data structures ───────────────────────────────────────────────


def _sample_dir(pipeline: str) -> Path:
    return SAMPLES_ROOT / pipeline


def _pending_path(pipeline: str) -> Path:
    return _sample_dir(pipeline) / ".pending.json"


def _approved_path(pipeline: str) -> Path:
    d = EXAMPLES_ROOT / pipeline
    d.mkdir(parents=True, exist_ok=True)
    return d / "from_samples.json"


def _text_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


# ── Public API ────────────────────────────────────────────────────


def scan_samples(pipeline: str) -> list[dict]:
    """샘플 폴더 스캔 → 파일 목록 반환."""
    if pipeline not in VALID_PIPELINES:
        return []

    sample_dir = _sample_dir(pipeline)
    if not sample_dir.exists():
        return []

    pending = _load_pending_hashes(pipeline)

    files = []
    for p in sorted(sample_dir.iterdir()):
        if p.suffix.lower() not in (".hwpx", ".hwp"):
            continue
        h = _text_hash(p.name + str(p.stat().st_size))
        files.append({
            "filename": p.name,
            "path": str(p),
            "size_kb": round(p.stat().st_size / 1024, 1),
            "status": "pending" if h in pending else "new",
        })
    return files


async def extract_and_analyze(
    pipeline: str,
    file_paths: list[str] | None = None,
) -> list[dict]:
    """HWPX 파일에서 텍스트 추출 + AI 분석 → 후보 예시 반환.

    file_paths가 None이면 해당 pipeline 폴더의 모든 .hwpx 파일 처리.
    """
    if pipeline not in VALID_PIPELINES:
        return []

    hwpx = HwpxService()
    sample_dir = _sample_dir(pipeline)

    if file_paths:
        targets = [Path(p) for p in file_paths]
    else:
        targets = sorted(
            p for p in sample_dir.iterdir()
            if p.suffix.lower() in (".hwpx", ".hwp")
        )

    candidates: list[dict] = []
    for fpath in targets:
        try:
            if fpath.suffix.lower() == ".hwpx":
                text = hwpx.read_text(fpath)
            else:
                log.warning("hwp_not_supported", file=fpath.name)
                candidates.append({
                    "filename": fpath.name,
                    "error": ".hwp 파일은 지원되지 않습니다. .hwpx로 변환 후 다시 시도하세요.",
                })
                continue

            if not text or len(text.strip()) < 20:
                candidates.append({
                    "filename": fpath.name,
                    "error": "텍스트를 추출할 수 없거나 내용이 너무 짧습니다.",
                })
                continue

            # Truncate very long documents for AI analysis
            analysis_text = text[:4000] if len(text) > 4000 else text

            metadata = await _ai_analyze(pipeline, analysis_text)
            candidate = _build_candidate(pipeline, fpath.name, text, metadata)
            candidates.append(candidate)

        except Exception as e:
            log.error("sample_extract_error", file=fpath.name, error=str(e))
            candidates.append({
                "filename": fpath.name,
                "error": f"추출 실패: {type(e).__name__}: {e}",
            })

    # Save to pending
    if candidates:
        _save_pending(pipeline, candidates)

    return candidates


def load_pending(pipeline: str) -> list[dict]:
    """대기 중인 후보 예시 로드."""
    path = _pending_path(pipeline)
    if not path.exists():
        return []
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return []


def approve_examples(pipeline: str, examples: list[dict]) -> dict:
    """검토 완료된 예시를 학습 데이터로 저장."""
    if pipeline not in VALID_PIPELINES:
        return {"error": "invalid pipeline"}

    approved_path = _approved_path(pipeline)

    # Load existing approved examples
    existing: list[dict] = []
    if approved_path.exists():
        try:
            existing = json.loads(approved_path.read_text(encoding="utf-8"))
        except Exception:
            existing = []

    # Check for duplicates via body hash
    existing_hashes = {_text_hash(e.get("expected_body", "")) for e in existing}

    added = 0
    skipped = 0
    for ex in examples:
        # Strip UI-only fields
        clean = _clean_for_storage(pipeline, ex)
        body_hash = _text_hash(clean.get("expected_body", ""))
        if body_hash in existing_hashes:
            skipped += 1
            continue
        existing.append(clean)
        existing_hashes.add(body_hash)
        added += 1

    # Save
    approved_path.write_text(
        json.dumps(existing, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    # Remove approved items from pending
    _remove_from_pending(pipeline, examples)

    return {"added": added, "skipped_duplicates": skipped, "total": len(existing)}


def reject_pending(pipeline: str, filenames: list[str] | None = None) -> dict:
    """대기 중인 후보 제거."""
    if filenames is None:
        # Clear all
        path = _pending_path(pipeline)
        if path.exists():
            path.unlink()
        return {"cleared": True}

    pending = load_pending(pipeline)
    remaining = [p for p in pending if p.get("filename") not in filenames]
    _save_pending_raw(pipeline, remaining)
    return {"removed": len(pending) - len(remaining)}


# ── AI analysis ───────────────────────────────────────────────────


async def _ai_analyze(pipeline: str, text: str) -> dict:
    """Ollama를 사용하여 문서 메타데이터 역추론."""
    prompt_template = _ANALYSIS_PROMPTS.get(pipeline)
    if not prompt_template:
        return {}

    prompt = prompt_template.format(body=text)

    try:
        from backend.ai.client import GptOssClient
        from backend.config import settings

        client = GptOssClient(settings.OLLAMA_BASE_URL, settings.OLLAMA_MODEL)
        result = await client.chat(
            messages=[{"role": "user", "content": prompt}],
            task="classify",
            temperature=0.1,
            max_tokens=512,
        )

        raw = result.get("content", "")
        return _parse_json_response(raw)

    except Exception as e:
        log.warning("ai_analyze_fallback", error=str(e))
        return {}


def _parse_json_response(raw: str) -> dict:
    """AI 응답에서 JSON 객체 추출 (마크다운 코드펜스 제거 포함)."""
    text = raw.strip()
    # Strip markdown code fences
    if text.startswith("```"):
        lines = text.split("\n")
        lines = [l for l in lines if not l.strip().startswith("```")]
        text = "\n".join(lines).strip()

    # Find first { ... } block
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        try:
            return json.loads(text[start : end + 1])
        except json.JSONDecodeError:
            pass
    return {}


# ── Candidate building ────────────────────────────────────────────


def _build_candidate(
    pipeline: str, filename: str, full_text: str, ai_metadata: dict
) -> dict:
    """파이프라인별 후보 예시 구성."""
    year = date.today().year

    if pipeline == "gianmun":
        return {
            "filename": filename,
            "doc_type": ai_metadata.get("doc_type", "일반기안"),
            "subject": ai_metadata.get("subject", ""),
            "instruction": ai_metadata.get("instruction", ""),
            "expected_body": full_text,
            "current_year": year,
        }
    elif pipeline == "docent":
        return {
            "filename": filename,
            "title": ai_metadata.get("title", ""),
            "target_count": ai_metadata.get("target_count", 10),
            "months": ai_metadata.get("months", 6),
            "expected_project_type": ai_metadata.get(
                "expected_project_type", "교육훈련"
            ),
            "expected_body": full_text,
            "current_year": year,
        }
    elif pipeline == "complaint":
        return {
            "filename": filename,
            "complaint_summary": ai_metadata.get("complaint_summary", ""),
            "expected_category": ai_metadata.get("expected_category", "기타"),
            "expected_department": ai_metadata.get("expected_department", ""),
            "expected_urgency": ai_metadata.get("expected_urgency", "medium"),
            "expected_body": full_text,
            "current_year": year,
        }
    elif pipeline == "meeting":
        return {
            "filename": filename,
            "title": ai_metadata.get("title", ""),
            "date": ai_metadata.get("date", ""),
            "attendees": ai_metadata.get("attendees", ""),
            "expected_summary": full_text,
            "current_year": year,
        }
    return {"filename": filename, "expected_body": full_text}


def _clean_for_storage(pipeline: str, example: dict) -> dict:
    """UI 전용 필드(filename, error) 제거 → 학습 데이터용 정제."""
    clean = {k: v for k, v in example.items() if k not in ("filename", "error", "status")}

    # Map fields to what auto_dataset expects
    if pipeline == "gianmun":
        # auto_dataset expects: user_request, doc_type, current_year, body
        return {
            "user_request": clean.get("instruction", clean.get("subject", "")),
            "doc_type": clean.get("doc_type", "일반기안"),
            "current_year": clean.get("current_year", date.today().year),
            "body": clean.get("expected_body", ""),
        }
    elif pipeline == "docent":
        return {
            "user_request": clean.get("title", ""),
            "target_count": clean.get("target_count", 10),
            "duration_months": clean.get("months", 6),
            "current_year": clean.get("current_year", date.today().year),
            "fiscal_year": clean.get("current_year", date.today().year),
            "total_krw": 0,
            "items": [],
        }
    elif pipeline == "complaint":
        return {
            "complaint_text": clean.get("complaint_summary", ""),
            "current_year": clean.get("current_year", date.today().year),
            "classification": clean.get("expected_category", "기타"),
            "response_body": clean.get("expected_body", ""),
        }
    elif pipeline == "meeting":
        return {
            "raw_content": clean.get("expected_summary", ""),
            "attendees": clean.get("attendees", ""),
            "current_year": clean.get("current_year", date.today().year),
            "summary": clean.get("expected_summary", ""),
        }
    return clean


# ── Pending file helpers ──────────────────────────────────────────


def _load_pending_hashes(pipeline: str) -> set[str]:
    pending = load_pending(pipeline)
    return {_text_hash(p.get("filename", "")) for p in pending}


def _save_pending(pipeline: str, candidates: list[dict]) -> None:
    existing = load_pending(pipeline)
    existing_names = {p.get("filename") for p in existing}
    for c in candidates:
        if c.get("filename") not in existing_names:
            existing.append(c)
    _save_pending_raw(pipeline, existing)


def _save_pending_raw(pipeline: str, data: list[dict]) -> None:
    path = _pending_path(pipeline)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _remove_from_pending(pipeline: str, approved: list[dict]) -> None:
    approved_names = {e.get("filename") for e in approved}
    pending = load_pending(pipeline)
    remaining = [p for p in pending if p.get("filename") not in approved_names]
    _save_pending_raw(pipeline, remaining)
