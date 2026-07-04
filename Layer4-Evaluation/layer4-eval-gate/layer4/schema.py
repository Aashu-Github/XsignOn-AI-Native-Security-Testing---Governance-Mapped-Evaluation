"""Common result schema so deepeval and RAGAS output can be consumed
uniformly downstream (the research doc's "results normalization" question).
Every tool's output gets flattened into a list of MetricResult before
anything else touches it.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class MetricResult:
    tool: str            # "deepeval" | "ragas"
    category: str        # OWASP id, e.g. "LLM01", or "ragas.faithfulness"
    label: str            # human-readable metric name
    score: float
    threshold: float
    passed: bool
    reason: str | None = None
    probe_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class GateRun:
    target_name: str
    target_type: str
    threshold_default: float
    results: list[MetricResult] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    @property
    def failures(self) -> list[MetricResult]:
        return [r for r in self.results if not r.passed]

    @property
    def blocked(self) -> bool:
        return len(self.failures) > 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "target_name": self.target_name,
            "target_type": self.target_type,
            "threshold_default": self.threshold_default,
            "timestamp": self.timestamp,
            "blocked": self.blocked,
            "results": [r.to_dict() for r in self.results],
        }
