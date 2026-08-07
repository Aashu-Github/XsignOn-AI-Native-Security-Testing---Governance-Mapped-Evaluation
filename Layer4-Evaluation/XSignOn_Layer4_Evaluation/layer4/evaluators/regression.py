from __future__ import annotations

from typing import Any

from layer4.models import MetricResult


class RegressionComparator:
    def __init__(self, config: dict[str, Any]):
        self.config = config

    def compare(self, current_aggregates: dict[str, Any], baseline_report: dict[str, Any] | None) -> dict[str, Any]:
        if not baseline_report:
            return {"status": "not_run", "reason": "No baseline run has been selected.", "comparisons": []}

        allowed_drop = float(self.config.get("thresholds", {}).get("maximum_regression_drop", 0.05))
        baseline_aggregates = baseline_report.get("aggregates", {})
        comparisons: list[dict[str, Any]] = []
        failed = False
        for metric, current in current_aggregates.items():
            current_mean = current.get("mean")
            baseline_mean = baseline_aggregates.get(metric, {}).get("mean")
            if current_mean is None or baseline_mean is None:
                continue
            delta = current_mean - baseline_mean
            passed = delta >= -allowed_drop
            failed = failed or not passed
            comparisons.append({
                "metric": metric,
                "current": current_mean,
                "baseline": baseline_mean,
                "delta": delta,
                "allowed_drop": allowed_drop,
                "passed": passed,
            })
        return {
            "status": "fail" if failed else "pass",
            "reason": "One or more metrics regressed beyond the allowed drop." if failed else "No comparable metric exceeded the regression allowance.",
            "comparisons": comparisons,
        }
