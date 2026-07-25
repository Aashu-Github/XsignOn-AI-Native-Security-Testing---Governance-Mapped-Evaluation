"""
Common normalized result schema.

Every scorer (Inspect AI, lm-eval-harness, deepeval, RAGAS) outputs its own
native format. This is the shape they all get flattened into before Layer 5
touches anything. This is the answer to the "results normalization" question
from the doc -- normalization happens here, right after each tool runs,
inside the orchestrator, not downstream in Layer 5.
"""

from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum


class Verdict(str, Enum):
    PASS = "pass"
    FAIL = "fail"
    SKIPPED = "skipped"  # e.g. RAGAS on a non-RAG target


@dataclass
class MetricResult:
    tool: str                  # "inspect_ai" | "lm_eval_harness" | "deepeval" | "ragas"
    metric: str                # e.g. "owasp_llm01_prompt_injection", "faithfulness"
    score: float | None        # 0.0-1.0, None if skipped
    threshold: float | None    # fail_under, None if no gate applies
    verdict: Verdict
    owasp_mapping: list[str] = field(default_factory=list)
    used_llm_judge: bool = False
    notes: str = ""


@dataclass
class Layer4Report:
    target_id: str
    target_type: str           # "chat" | "rag"
    run_mode: str               # "pre_deploy_gate" | "scheduled_drift"
    started_at: str
    finished_at: str
    metrics: list[MetricResult] = field(default_factory=list)

    @property
    def overall_verdict(self) -> Verdict:
        if any(m.verdict == Verdict.FAIL for m in self.metrics):
            return Verdict.FAIL
        return Verdict.PASS

    def to_dict(self) -> dict:
        d = asdict(self)
        d["overall_verdict"] = self.overall_verdict.value
        return d


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
