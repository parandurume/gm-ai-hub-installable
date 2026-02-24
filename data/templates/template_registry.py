"""HWPX 템플릿 레지스트리 — 7종 공문서 템플릿 관리

템플릿은 Python dict 기반으로 관리되며, HWPX 생성 시 hwpx_service를 사용해
동적으로 문서를 생성합니다. {{field}} 플레이스홀더를 지원합니다.
"""

from datetime import date

TEMPLATE_REGISTRY = {
    "일반기안": {
        "id": "general_draft",
        "name": "일반기안",
        "description": "일반적인 기안문 양식",
        "fields": ["subject", "body", "drafter", "department"],
    },
    "협조전": {
        "id": "cooperation",
        "name": "협조전",
        "description": "부서 간 협조 요청 문서",
        "fields": ["subject", "to_department", "body", "drafter", "department"],
    },
    "보고서": {
        "id": "report",
        "name": "보고서",
        "description": "업무 보고서 양식",
        "fields": ["subject", "body", "drafter", "department", "period"],
    },
    "계획서": {
        "id": "plan",
        "name": "계획서",
        "description": "사업 계획서 양식",
        "fields": ["subject", "body", "drafter", "department", "budget", "timeline"],
    },
    "결과보고서": {
        "id": "result_report",
        "name": "결과보고서",
        "description": "사업 결과보고서 양식",
        "fields": ["subject", "body", "drafter", "department", "outcomes", "budget_execution"],
    },
    "회의록": {
        "id": "meeting_minutes",
        "name": "회의록",
        "description": "회의록 양식",
        "fields": ["subject", "date", "attendees", "agenda", "decisions", "action_items"],
    },
    "민원답변": {
        "id": "complaint_response",
        "name": "민원답변",
        "description": "민원 답변 문서 양식",
        "fields": ["subject", "complainant", "complaint_summary", "response_body", "drafter", "department"],
    },
}


TEMPLATE_CONTENT = {
    "일반기안": """
{subject}

1. 목적
{body}

2. 세부 내용
  상기 내용과 같이 기안합니다.

작성자: {drafter}
부서: {department}
작성일: {date}
""",
    "협조전": """
{subject}

수신: {to_department}

1. 관련
  귀 부서의 무궁한 발전을 기원합니다.

2. 협조 요청 사항
{body}

3. 협조 기한
  상기 내용에 대해 협조하여 주시기 바랍니다.

작성자: {drafter}
부서: {department}
작성일: {date}
""",
    "보고서": """
{subject}

보고 기간: {period}

1. 개요
{body}

2. 주요 내용

3. 향후 계획

작성자: {drafter}
부서: {department}
작성일: {date}
""",
    "계획서": """
{subject}

1. 추진 배경 및 목적
{body}

2. 추진 기간 및 일정
{timeline}

3. 예산 계획
{budget}

4. 세부 추진 내용

5. 기대 효과

작성자: {drafter}
부서: {department}
작성일: {date}
""",
    "결과보고서": """
{subject}

1. 사업 개요
{body}

2. 추진 실적 및 성과
{outcomes}

3. 예산 집행 현황
{budget_execution}

4. 향후 계획 및 건의사항

작성자: {drafter}
부서: {department}
작성일: {date}
""",
    "회의록": """
{subject}

회의일시: {date}
참석자: {attendees}

1. 안건
{agenda}

2. 논의 내용

3. 결정 사항
{decisions}

4. 조치 사항
{action_items}

작성일: {date}
""",
    "민원답변": """
{subject}

민원인: {complainant}

1. 민원 요지
{complaint_summary}

2. 답변 내용
{response_body}

3. 관련 법령 및 근거

  상기와 같이 답변드리오니, 양해하여 주시기 바랍니다.

작성자: {drafter}
부서: {department}
작성일: {date}
""",
}


def render_template(template_name: str, fields: dict) -> str:
    """템플릿에 필드 값을 주입하여 텍스트를 생성합니다.

    - date 필드는 항상 동적으로 주입 (RULE-01)
    - 누락된 필드는 빈 문자열로 대체
    """
    if template_name not in TEMPLATE_CONTENT:
        raise ValueError(f"Unknown template: {template_name}")

    content = TEMPLATE_CONTENT[template_name]

    # 항상 현재 날짜 주입 (RULE-01: 동적 연도)
    defaults = {
        "date": date.today().strftime("%Y-%m-%d"),
        "drafter": "",
        "department": "",
    }
    merged = {**defaults, **fields}

    # 플레이스홀더 치환
    for key, value in merged.items():
        placeholder = "{" + key + "}"
        if isinstance(value, list):
            value = ", ".join(str(v) for v in value)
        content = content.replace(placeholder, str(value))

    return content.strip()


def list_templates() -> list[str]:
    """사용 가능한 템플릿 이름 목록을 반환합니다."""
    return list(TEMPLATE_REGISTRY.keys())


def get_template_info(template_name: str) -> dict | None:
    """템플릿 메타데이터를 반환합니다."""
    return TEMPLATE_REGISTRY.get(template_name)
