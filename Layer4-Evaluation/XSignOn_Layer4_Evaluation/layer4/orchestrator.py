from __future__ import annotations

import hashlib
import os
import platform
import sys
import uuid
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from layer4.config import ROOT, resolve_project_path
from layer4.datasets import MedicalCaseGenerator
from layer4.evaluators import (
    ConsistencyEvaluator,
    DeepEvalEvaluator,
    DeterministicEvaluator,
    RagasEvaluator,
    SafetyEvaluator,
)
from layer4.evaluators.calibration import JudgeCalibration
from layer4.evaluators.owasp import OwaspCoverage
from layer4.evaluators.regression import RegressionComparator
from layer4.models import MetricResult
from layer4.reporting import render_html_report
from layer4.storage import RunStorage
from layer4.targets import create_target
from layer4.utils import mean, percentile, stable_hash, utc_now_iso


ProgressCallback = Callable[[dict[str, Any]], None]


def _aggregate(metrics: list[dict[str, Any]]) -> dict[str, Any]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in metrics:
        grouped[row["metric"]].append(row)
    output: dict[str, Any] = {}
    for name, rows in grouped.items():
        scores = [float(row["score"]) for row in rows if row.get("score") is not None]
        pass_values = [1.0 if row.get("passed") else 0.0 for row in rows if row.get("passed") is not None]
        output[name] = {
            "mean": mean(scores),
            "minimum": min(scores) if scores else None,
            "maximum": max(scores) if scores else None,
            "pass_rate": mean(pass_values),
            "count": len(rows),
            "error_count": sum(1 for row in rows if row.get("error")),
        }
    return output


def _gate(config: dict[str, Any], metrics: list[dict[str, Any]], regression: dict[str, Any], calibration: dict[str, Any]) -> dict[str, Any]:
    failures = [row for row in metrics if row.get("passed") is False]
    critical_failures = [row for row in failures if row.get("severity") == "critical"]
    fail_on_any = bool(config.get("gating", {}).get("fail_on_any_metric", False))
    require_calibration = bool(config.get("gating", {}).get("require_judge_calibration", False))
    reasons: list[str] = []
    if critical_failures:
        reasons.append(f"{len(critical_failures)} critical check(s) failed")
    if fail_on_any and failures:
        reasons.append(f"{len(failures)} total check(s) failed")
    if regression.get("status") == "fail":
        reasons.append("regression threshold exceeded")
    if require_calibration and calibration.get("status") != "pass":
        reasons.append("judge calibration is not valid")
    verdict = "FAIL" if reasons else "PASS"
    return {
        "verdict": verdict,
        "reasons": reasons or ["All configured hard gates passed."],
        "critical_failure_count": len(critical_failures),
        "failure_count": len(failures),
    }


class EvaluationOrchestrator:
    def __init__(self, config: dict[str, Any], storage: RunStorage | None = None):
        self.config = config
        self.storage = storage or RunStorage()

    def run(self, run_id: str | None = None, progress: ProgressCallback | None = None) -> dict[str, Any]:
        run_id = run_id or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:8]
        notify = progress or (lambda _: None)
        notify({"stage": "generating_cases", "progress": 5, "message": "Generating row-specific medical test cases"})

        dataset_path = resolve_project_path(self.config["dataset"]["path"])
        generator = MedicalCaseGenerator(dataset_path, seed=int(self.config["run"].get("seed", 42)))
        cases = generator.generate(
            max_records=int(self.config["run"].get("max_records", 6)),
            include_case_types=self.config["run"].get("include_case_types"),
        )

        notify({"stage": "executing_target", "progress": 12, "message": f"Executing {len(cases)} cases"})
        target = create_target(self.config["target"])
        traces = []
        repeat_count = max(1, int(self.config["run"].get("repeat_count", 1)))
        total = len(cases) * repeat_count
        completed = 0
        for attempt in range(1, repeat_count + 1):
            for case in cases:
                trace = target.execute(run_id, case, attempt=attempt)
                traces.append(trace)
                completed += 1
                notify({
                    "stage": "executing_target",
                    "progress": 12 + int(43 * completed / max(total, 1)),
                    "message": f"Executed {completed}/{total}: {case.case_id}",
                })

        notify({"stage": "evaluating", "progress": 58, "message": "Running deterministic and policy evaluators"})
        evaluators = [
            DeterministicEvaluator(self.config),
            SafetyEvaluator(self.config),
            ConsistencyEvaluator(self.config),
            DeepEvalEvaluator(self.config),
            RagasEvaluator(self.config),
        ]
        metric_objects: list[MetricResult] = []
        for index, evaluator in enumerate(evaluators, start=1):
            notify({"stage": "evaluating", "progress": 58 + index * 6, "message": f"Running {evaluator.name}"})
            try:
                metric_objects.extend(evaluator.evaluate(cases, traces))
            except Exception as exc:
                metric_objects.append(MetricResult(
                    case_id="__run__",
                    metric=f"{evaluator.name}_execution",
                    score=0.0,
                    threshold=1.0,
                    passed=False,
                    evaluator=evaluator.name,
                    reason=f"{evaluator.name} failed and no fallback score was generated.",
                    severity="critical",
                    error=f"{type(exc).__name__}: {exc}",
                ))

        metric_rows = [item.to_dict() for item in metric_objects]
        trace_rows = [trace.to_dict() for trace in traces]
        case_rows = [case.to_dict() for case in cases]
        aggregates = _aggregate(metric_rows)

        notify({"stage": "regression", "progress": 90, "message": "Comparing with baseline and building OWASP evidence"})
        baseline_report = self.storage.get_baseline_report()
        regression = RegressionComparator(self.config).compare(aggregates, baseline_report)
        calibration = JudgeCalibration(
            resolve_project_path(self.config["judge"].get("human_ratings_path", "data/human_ratings.csv")),
            self.config,
        ).run(metric_rows)
        owasp = OwaspCoverage(ROOT / "evidence" / "sbom.json").build(metric_rows, trace_rows)
        gate = _gate(self.config, metric_rows, regression, calibration)
        failures = [row for row in metric_rows if row.get("passed") is False]

        manifest = {
            "target_provider": target.provider,
            "target_model": target.model,
            "judge_provider": self.config.get("judge", {}).get("provider"),
            "judge_model": self.config.get("judge", {}).get("model"),
            "deepeval_enabled": bool(self.config.get("judge", {}).get("enable_deepeval")),
            "ragas_enabled": bool(self.config.get("judge", {}).get("enable_ragas")),
            "enabled_metrics": list(self.config.get("metrics", {}).get("enabled", [])),
            "dataset_path": str(dataset_path),
            "dataset_sha256": hashlib.sha256(dataset_path.read_bytes()).hexdigest(),
            "case_suite_sha256": stable_hash(case_rows),
            "owasp_taxonomy": "OWASP GenAI/LLM Top 10 2026",
            "python_version": sys.version.split()[0],
            "platform": platform.platform(),
            "baseline_run_id": self.storage.get_baseline_id(),
            "api_keys_stored": False,
        }
        report = {
            "run_id": run_id,
            "created_at": utc_now_iso(),
            "manifest": manifest,
            "summary": {
                "case_count": len(cases),
                "trace_count": len(traces),
                "metric_count": len(metric_rows),
                "target_error_count": sum(1 for trace in traces if trace.error),
            },
            "gate": gate,
            "aggregates": aggregates,
            "owasp": owasp,
            "regression": regression,
            "judge_calibration": calibration,
            "failures": failures,
            "metrics": metric_rows,
        }
        html = render_html_report(report)
        directory = self.storage.save_run(run_id, self.config, case_rows, trace_rows, metric_rows, report, html)
        report["artifacts"] = {
            "directory": str(directory),
            "report_json": str(directory / "report.json"),
            "report_html": str(directory / "report.html"),
            "cases": str(directory / "cases.jsonl"),
            "traces": str(directory / "traces.jsonl"),
            "metrics": str(directory / "metrics.jsonl"),
        }
        # Save once more with artifact paths included.
        from layer4.utils import write_json
        write_json(directory / "report.json", report)
        notify({"stage": "complete", "progress": 100, "message": f"Evaluation complete: {gate['verdict']}"})
        return report
