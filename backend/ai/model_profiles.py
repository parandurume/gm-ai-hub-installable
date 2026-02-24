"""모델 프로파일 정의 (9개 빌트인 모델 + 동적 감지)."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

# (prefix, family, supports_thinking) — 순서 중요: 긴 접두사 우선
FAMILY_PATTERNS: list[tuple[str, str, bool]] = [
    ("gpt-oss", "gpt-oss", False),
    ("qwen3.5", "qwen3.5", True),
    ("qwen3", "qwen3", True),
    ("exaone4", "exaone", False),
    ("exaone3.5", "exaone", False),
    ("exaone3", "exaone", False),
    ("exaone", "exaone", False),
    ("deepseek-r1", "deepseek-r1", True),
    ("phi4", "phi4", False),
    ("phi3", "phi3", False),
    ("llama3.2", "llama3.2", False),
    ("llama3", "llama3", False),
    ("hyperclovax", "hyperclovax", False),
    ("gemma", "gemma", False),
    ("mistral", "mistral", False),
]


def detect_family(model_name: str) -> tuple[str, bool]:
    """모델 이름에서 패밀리와 thinking 지원 여부 추론."""
    base = model_name.split("/")[-1].lower()
    for prefix, family, thinking in FAMILY_PATTERNS:
        if base.startswith(prefix):
            return family, thinking
    return "unknown", False


def extract_param_size(model_name: str) -> int:
    """태그에서 파라미터 크기 추출 (e.g., ':8b' → 8, ':120b-cloud' → 120)."""
    m = re.search(r":(\d+(?:\.\d+)?)b", model_name.lower())
    return int(float(m.group(1))) if m else 0


@dataclass
class ModelProfile:
    id: str
    name: str
    family: str
    param_size: int  # 억 파라미터
    ram_gb: int  # 최소 RAM (GB)
    supports_thinking: bool
    context_len: int
    strengths: list[str] = field(default_factory=list)
    best_for: list[str] = field(default_factory=list)

    @classmethod
    def from_ollama(cls, data: dict) -> "ModelProfile":
        """Ollama API 응답에서 프로파일 생성 (패밀리 자동 감지)."""
        name = data["name"]
        family, thinking = detect_family(name)
        param = extract_param_size(name)
        return cls(
            id=name,
            name=name,
            family=family,
            param_size=param,
            ram_gb=max(4, param) if param else 8,
            supports_thinking=thinking,
            context_len=32768 if family != "unknown" else 4096,
            strengths=[],
            best_for=[],
        )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "family": self.family,
            "param_size": self.param_size,
            "ram_gb": self.ram_gb,
            "supports_thinking": self.supports_thinking,
            "context_len": self.context_len,
            "strengths": self.strengths,
            "best_for": self.best_for,
        }


BUILTIN_PROFILES: dict[str, ModelProfile] = {
    "gpt-oss:20b": ModelProfile(
        id="gpt-oss:20b",
        name="GPT-OSS 20B",
        family="gpt-oss",
        param_size=20,
        ram_gb=14,
        supports_thinking=False,
        context_len=32768,
        strengths=["한국어", "공문서", "안정성"],
        best_for=["gianmun_body", "plan_document", "budget_calc"],
    ),
    "qwen3:8b": ModelProfile(
        id="qwen3:8b",
        name="Qwen3 8B",
        family="qwen3",
        param_size=8,
        ram_gb=6,
        supports_thinking=True,
        context_len=32768,
        strengths=["빠른응답", "분류", "요약"],
        best_for=["classify", "summarize", "incoming_doc"],
    ),
    "qwen3:14b": ModelProfile(
        id="qwen3:14b",
        name="Qwen3 14B",
        family="qwen3",
        param_size=14,
        ram_gb=10,
        supports_thinking=True,
        context_len=32768,
        strengths=["균형", "한국어", "추론"],
        best_for=["gianmun_body", "complaint_resp", "meeting_minutes"],
    ),
    "qwen3:32b": ModelProfile(
        id="qwen3:32b",
        name="Qwen3 32B",
        family="qwen3",
        param_size=32,
        ram_gb=22,
        supports_thinking=True,
        context_len=32768,
        strengths=["고품질", "추론", "계획서", "예산"],
        best_for=["plan_document", "budget_calc", "docent_plan"],
    ),
    "qwen3:30b-a3b": ModelProfile(
        id="qwen3:30b-a3b",
        name="Qwen3 30B-A3B (MoE)",
        family="qwen3",
        param_size=30,
        ram_gb=18,
        supports_thinking=True,
        context_len=32768,
        strengths=["MoE효율", "추론", "계획서"],
        best_for=["plan_document", "docent_plan"],
    ),
    "qwen3.5:72b": ModelProfile(
        id="qwen3.5:72b",
        name="Qwen3.5 72B",
        family="qwen3.5",
        param_size=72,
        ram_gb=48,
        supports_thinking=True,
        context_len=131072,
        strengths=["최고품질", "추론", "긴문서"],
        best_for=["docent_plan", "budget_calc", "plan_document"],
    ),
    "exaone3.5:7.8b": ModelProfile(
        id="exaone3.5:7.8b",
        name="EXAONE 3.5 7.8B",
        family="exaone",
        param_size=8,
        ram_gb=6,
        supports_thinking=False,
        context_len=32768,
        strengths=["한국어특화", "공문서", "빠른응답"],
        best_for=["classify", "gianmun_body", "complaint_resp"],
    ),
    "deepseek-r1:8b": ModelProfile(
        id="deepseek-r1:8b",
        name="DeepSeek-R1 8B",
        family="deepseek-r1",
        param_size=8,
        ram_gb=6,
        supports_thinking=True,
        context_len=32768,
        strengths=["추론", "수학", "예산계산"],
        best_for=["budget_calc", "classify"],
    ),
    "deepseek-r1:14b": ModelProfile(
        id="deepseek-r1:14b",
        name="DeepSeek-R1 14B",
        family="deepseek-r1",
        param_size=14,
        ram_gb=10,
        supports_thinking=True,
        context_len=32768,
        strengths=["추론", "수학", "계획"],
        best_for=["budget_calc", "plan_document"],
    ),
    "joonoh/HyperCLOVAX-SEED-Text-Instruct-1.5B": ModelProfile(
        id="joonoh/HyperCLOVAX-SEED-Text-Instruct-1.5B",
        name="HyperCLOVA X 1.5B",
        family="hyperclovax",
        param_size=2,
        ram_gb=2,
        supports_thinking=False,
        context_len=4096,
        strengths=["한국어특화", "경량", "빠른응답"],
        best_for=["classify", "summarize"],
    ),
    "phi4:latest": ModelProfile(
        id="phi4:latest",
        name="Phi-4",
        family="phi4",
        param_size=14,
        ram_gb=9,
        supports_thinking=False,
        context_len=16384,
        strengths=["경량", "영어", "코드"],
        best_for=["classify", "summarize"],
    ),
}
