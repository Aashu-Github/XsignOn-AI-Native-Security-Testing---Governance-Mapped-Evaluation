from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from layer4.models import ExecutionTrace, MetricResult, TestCase


class EvaluationError(RuntimeError):
    pass


class Evaluator(ABC):
    name = "evaluator"

    def __init__(self, config: dict[str, Any]):
        self.config = config
        enabled = config.get("metrics", {}).get("enabled")
        self.enabled_metrics = set(enabled) if isinstance(enabled, list) else None

    def metric_enabled(self, metric_name: str) -> bool:
        """Return whether a user-selectable metric should execute.

        A missing list means backward-compatible behavior: all metrics are enabled.
        Technical integrity checks are handled separately by the orchestrator/evaluators.
        """
        return self.enabled_metrics is None or metric_name in self.enabled_metrics

    @abstractmethod
    def evaluate(self, cases: list[TestCase], traces: list[ExecutionTrace]) -> list[MetricResult]:
        raise NotImplementedError
