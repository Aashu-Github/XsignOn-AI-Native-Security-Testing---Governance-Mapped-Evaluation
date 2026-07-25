"""
Stand-in for lm-evaluation-harness (EleutherAI). Real version: shell out to
`lm_eval --model ... --tasks ... --output_path ...` and parse the JSON it
writes. This is the general-robustness baseline, not security-focused --
its job is to catch "the security patch broke basic reasoning."

Implements the PR-vs-nightly split raised in the questions: a small fast
subset runs on every PR, the full ~200-task suite only runs on the nightly
drift schedule.
"""

from layer4.scorers.base import BaseScorer
from layer4.schema import MetricResult

FAST_SUBSET = ["arc_easy", "hellaswag", "gsm8k_lite"]
FULL_SUITE = FAST_SUBSET + ["mmlu", "truthfulqa", "winogrande", "bbh"]  # +190 more in reality


class LMEvalHarnessScorer(BaseScorer):
    name = "lm_eval_harness"
    requires_llm_judge = False

    def applies_to(self, target_cfg: dict) -> bool:
        return True

    def score(self, target_cfg: dict, transcripts: list[dict], client=None) -> list[MetricResult]:
        run_mode = target_cfg.get("run_mode", "pre_deploy_gate")
        tasks = FAST_SUBSET if run_mode == "pre_deploy_gate" else FULL_SUITE
        seed_base = target_cfg["target_id"]
        results = []
        for task in tasks:
            score = self._pseudo_score(f"lmeval:{seed_base}:{task}")
            threshold = target_cfg.get("thresholds", {}).get("lm_eval_harness", {}).get(task, 0.60)
            results.append(MetricResult(
                tool=self.name,
                metric=f"robustness_baseline.{task}",
                score=score,
                threshold=threshold,
                verdict=self._verdict(score, threshold),
                owasp_mapping=[],  # not a security tool
                used_llm_judge=False,
                notes=f"{'fast subset (PR gate)' if run_mode == 'pre_deploy_gate' else 'full suite (nightly)'}",
            ))
        return results
