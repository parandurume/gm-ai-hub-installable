"""DSPy 설정 — Ollama 연결 + 최적화 파이프라인 로드."""

from __future__ import annotations

import json
from pathlib import Path

import dspy


def configure_dspy(
    model: str = "gpt-oss:20b",
    base_url: str = "http://127.0.0.1:11434",
) -> dspy.LM:
    """DSPy LM 설정 + Ollama 연결."""
    lm = dspy.LM(
        model=f"ollama_chat/{model}",
        api_base=base_url,
        api_key="ollama",
        temperature=0.1,
        max_tokens=8192,
        cache=False,
    )
    dspy.configure(lm=lm)
    return lm


def load_optimized_pipeline(
    pipeline_instance, pipeline_name: str, model: str
) -> bool:
    """최적화된 파이프라인 파일 자동 로드 (RULE-14)."""
    from backend import paths
    opt_dir = paths.optimized_pipelines_dir() / pipeline_name
    if not opt_dir.exists():
        return False

    model_tag = model.replace(":", "-").replace("/", "_")

    # 이 모델에 맞는 최적화 파일 검색 (최신 날짜 우선)
    candidates = sorted(opt_dir.glob(f"v_{model_tag}_*.json"), reverse=True)

    # 없으면 다른 모델의 최적화 파일도 시도
    if not candidates:
        candidates = sorted(opt_dir.glob("v_*.json"), reverse=True)

    if not candidates:
        return False

    try:
        pipeline_instance.load(str(candidates[0]))
        meta_path = (
            str(candidates[0]).replace(".json", "").replace("v_", "meta_")
            + ".json"
        )
        if Path(meta_path).exists():
            meta = json.loads(Path(meta_path).read_text())
            print(
                f"  최적화 파이프라인 로드: {pipeline_name}"
                f" (모델: {meta.get('model')}, 점수: {meta.get('val_score', 'N/A'):.3f})"
            )
        return True
    except Exception as e:
        print(f"  최적화 파일 로드 실패: {e}")
        return False
