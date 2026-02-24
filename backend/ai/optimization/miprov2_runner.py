"""
MIPROv2 최적화 실행기 (RULE-13: num_threads=1).

사용법:
  python -m backend.ai.optimization.miprov2_runner \\
    --pipeline gianmun --model qwen3:32b --trials 15
"""

from __future__ import annotations

import argparse
import asyncio
import json
from datetime import date, datetime
from pathlib import Path

import dspy
from dspy.teleprompt import MIPROv2

from backend.ai.dspy_config import configure_dspy
from backend.ai.optimization.auto_dataset import build_dataset
from backend.ai.optimization.metrics import combined_metric
from backend.ai.pipelines import (
    AiDocentPlanPipeline,
    ComplaintDraftPipeline,
    GianmunBodyPipeline,
    MeetingSummaryPipeline,
)

PIPELINE_MAP = {
    "docent": AiDocentPlanPipeline,
    "gianmun": GianmunBodyPipeline,
    "complaint": ComplaintDraftPipeline,
    "meeting": MeetingSummaryPipeline,
}

METRIC_MAP = {
    "docent": combined_metric,
    "gianmun": combined_metric,
    "complaint": combined_metric,
    "meeting": combined_metric,
}


async def run_optimization(
    pipeline_name: str,
    model: str,
    num_trials: int = 15,
    max_bootstrapped_demos: int = 3,
    max_labeled_demos: int = 4,
    num_candidates: int = 10,
) -> tuple | None:
    """MIPROv2로 지정 파이프라인을 최적화한다."""
    print(f"\n{'=' * 60}")
    print(f"MIPROv2 최적화 시작")
    print(f"  파이프라인: {pipeline_name}")
    print(f"  모델:       {model}")
    print(f"  시도 횟수:  {num_trials}")
    print(f"{'=' * 60}\n")

    # 1. DSPy 설정
    configure_dspy(model=model)

    # 2. 파이프라인 생성
    PipelineClass = PIPELINE_MAP[pipeline_name]
    pipeline = PipelineClass()

    # 3. 데이터셋
    print("데이터셋 로드 중...")
    trainset, devset = await build_dataset(pipeline_name, min_examples=10)
    print(f"   학습: {len(trainset)}개, 검증: {len(devset)}개")

    if len(trainset) < 5:
        print(f"  학습 예시가 5개 미만입니다. data/examples/{pipeline_name}/ 에 추가하세요.")
        return None

    # 4. MIPROv2 설정 (RULE-13: num_threads=1)
    metric = METRIC_MAP[pipeline_name]
    optimizer = MIPROv2(
        metric=metric,
        auto="medium",
        num_candidates=num_candidates,
        max_bootstrapped_demos=max_bootstrapped_demos,
        max_labeled_demos=max_labeled_demos,
        num_threads=1,  # RULE-13
    )

    # 5. 최적화 실행
    print("\nMIPROv2 최적화 실행 중... (30~90분 소요)")
    optimized = optimizer.compile(
        pipeline,
        trainset=trainset,
        num_trials=num_trials,
        minibatch_size=min(5, len(trainset)),
        minibatch_full_eval_steps=5,
        requires_permission_to_run=False,
    )

    # 6. 검증
    print("\n검증 세트 평가 중...")
    val_scores = []
    for example in devset[:10]:
        try:
            pred = optimized(**example.inputs().toDict())
            score = metric(example, pred)
            val_scores.append(score)
        except Exception as e:
            print(f"  평가 오류: {e}")

    avg_score = sum(val_scores) / len(val_scores) if val_scores else 0.0

    # 7. 저장 (RULE-14)
    from backend import paths
    save_dir = paths.optimized_pipelines_dir() / pipeline_name
    save_dir.mkdir(parents=True, exist_ok=True)

    model_tag = model.replace(":", "-").replace("/", "_")
    today_str = date.today().strftime("%Y%m%d")
    save_path = save_dir / f"v_{model_tag}_{today_str}.json"

    optimized.save(str(save_path))

    meta = {
        "pipeline": pipeline_name,
        "model": model,
        "optimized_at": datetime.now().isoformat(),
        "num_trials": num_trials,
        "val_score": avg_score,
        "train_examples": len(trainset),
        "save_path": str(save_path),
    }
    meta_path = save_dir / f"meta_{model_tag}_{today_str}.json"
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2))

    print(f"\n최적화 완료! 저장: {save_path}, 점수: {avg_score:.3f}")
    return optimized, meta


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="MIPROv2 파이프라인 최적화")
    parser.add_argument("--pipeline", required=True,
                        choices=["docent", "gianmun", "complaint", "meeting"])
    parser.add_argument("--model", default="qwen3:32b")
    parser.add_argument("--trials", type=int, default=15)
    parser.add_argument("--max-bootstrapped-demos", type=int, default=3)
    parser.add_argument("--max-labeled-demos", type=int, default=4)
    parser.add_argument("--num-candidates", type=int, default=10)
    args = parser.parse_args()

    asyncio.run(run_optimization(
        pipeline_name=args.pipeline, model=args.model,
        num_trials=args.trials,
        max_bootstrapped_demos=args.max_bootstrapped_demos,
        max_labeled_demos=args.max_labeled_demos,
        num_candidates=args.num_candidates,
    ))
