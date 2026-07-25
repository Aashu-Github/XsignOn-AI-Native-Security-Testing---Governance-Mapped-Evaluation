"""
Every scorer plugs in through this interface. In production, `score()` would
shell out to the real tool (subprocess, SDK call, or a k8s Job it dispatches
and polls). Here, it runs a deterministic pseudo-scorer so the pipeline is
runnable end to end without API keys, GPUs, or the real dependency stack.

Swap the body of `score()` for a real call and nothing else in the pipeline
has to change -- that's the point of the common interface.
"""

from __future__ import annotations
import hashlib
from abc import ABC, abstractmethod
from layer4.schema import MetricResult, Verdict


class BaseScorer(ABC):
    name: str = "base"
    requires_llm_judge: bool = False

    @abstractmethod
    def applies_to(self, target_cfg: dict) -> bool:
        """Whether this scorer should run at all for this target.
        (This is where RAGAS's conditional-activation logic lives.)"""
        raise NotImplementedError

    @abstractmethod
    def score(self, target_cfg: dict, transcripts: list[dict], client=None) -> list[MetricResult]:
        """`client`, if provided, is an OllamaClient the scorer MAY use for
        real LLM-as-judge calls. Scorers that don't need a judge (Inspect AI,
        lm-eval-harness) just ignore it."""
        raise NotImplementedError

    def _judge_or_pseudo(self, client, rubric_prompt: str, pseudo_seed: str) -> tuple[float, str, bool]:
        """If a live client was given, this scorer is running in live mode --
        a real judge call is REQUIRED. Any failure (unreachable server,
        unparseable response) raises OllamaUnavailable rather than silently
        substituting a fake score; the caller decides how to surface that.

        Only when no client was given at all (plain pseudo/demo mode, not
        live mode) does this return a pseudo-score, seeded from the actual
        rubric/transcript content so different input files still vary."""
        if client is not None:
            score, reason = client.judge_score(rubric_prompt)  # raises OllamaUnavailable on failure
            return score, f"live judge ({client.model}): {reason}", True

        content_hash = hashlib.sha256(rubric_prompt.encode()).hexdigest()[:12]
        seed_with_content = f"{pseudo_seed}:{content_hash}"
        return self._pseudo_score(seed_with_content), "pseudo-score (demo mode, no live client)", False

    @staticmethod
    def _pseudo_score(seed: str, low: float = 0.55, high: float = 0.99) -> float:
        """Deterministic stand-in for a real eval score. Same transcript set
        + same metric name always produces the same 'score', so re-runs are
        reproducible like the real tools claim to be."""
        h = hashlib.sha256(seed.encode()).hexdigest()
        frac = int(h[:8], 16) / 0xFFFFFFFF
        return round(low + frac * (high - low), 4)

    @staticmethod
    def _verdict(score: float | None, threshold: float | None) -> Verdict:
        if score is None:
            return Verdict.SKIPPED
        if threshold is None:
            return Verdict.PASS
        return Verdict.PASS if score >= threshold else Verdict.FAIL
