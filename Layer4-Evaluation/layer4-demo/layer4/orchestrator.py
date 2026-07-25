"""
The actual Layer 4 entrypoint. In production this is what a k8s Job (pre-
deploy gate) or CronJob (scheduled drift) runs. It:

  1. loads scored attack transcripts (Layer 2/3 output)
  2. figures out which scorers apply to this target (RAGAS conditional logic)
  3. runs each one and normalizes its output into MetricResult
  4. hands the assembled Layer4Report to the gate

Each scorer stub owns its own container image in prod (per the doc's
question about combined-vs-separate images) -- this orchestrator doesn't
care, it just calls `.score()` on whatever's registered.
"""

from layer4.schema import Layer4Report, now_iso
from layer4.scorers.inspect_ai_stub import InspectAIScorer
from layer4.scorers.lm_eval_stub import LMEvalHarnessScorer
from layer4.scorers.deepeval_stub import DeepEvalScorer
from layer4.scorers.ragas_stub import RagasScorer

REGISTERED_SCORERS = [
    InspectAIScorer(),
    LMEvalHarnessScorer(),
    DeepEvalScorer(),
    RagasScorer(),
]


def run_layer4(target_cfg: dict, transcripts: list[dict], client=None) -> Layer4Report:
    """`client`, if given, is a live OllamaClient. Passed through to every
    scorer; scorers that don't need a judge ignore it, deepeval/RAGAS use it
    for real scoring when available."""
    started = now_iso()
    report = Layer4Report(
        target_id=target_cfg["target_id"],
        target_type=target_cfg.get("target_type", "chat"),
        run_mode=target_cfg.get("run_mode", "pre_deploy_gate"),
        started_at=started,
        finished_at="",  # filled at the end
    )

    for scorer in REGISTERED_SCORERS:
        if not scorer.applies_to(target_cfg):
            continue
        results = scorer.score(target_cfg, transcripts, client=client)
        report.metrics.extend(results)

    report.finished_at = now_iso()
    return report
