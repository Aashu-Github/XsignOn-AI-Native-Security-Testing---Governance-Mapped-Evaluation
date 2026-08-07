from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from layer4.config import ROOT, load_config
from layer4.datasets.medical import MedicalCaseGenerator
from layer4.orchestrator import EvaluationOrchestrator
from layer4.storage import RunStorage


class CoreEvaluationTests(unittest.TestCase):
    def test_case_generation_is_row_specific(self):
        generator = MedicalCaseGenerator(ROOT / "data" / "healthcare-dataset-stroke-data.csv", seed=42)
        cases = generator.generate(max_records=3)
        extraction = [case for case in cases if case.case_type == "structured_extraction"]
        self.assertEqual(len(extraction), 3)
        expected_outputs = [json.dumps(case.expected_output, sort_keys=True) for case in extraction]
        self.assertEqual(len(set(expected_outputs)), 3)

    def test_core_run_creates_real_artifacts(self):
        config = load_config(overrides={
            "run": {"max_records": 2, "repeat_count": 1},
            "judge": {"enable_deepeval": False, "enable_ragas": False},
            "target": {"provider": "local-record", "model": "local-record-v1"},
        })
        with tempfile.TemporaryDirectory() as temp:
            storage = RunStorage(Path(temp))
            report = EvaluationOrchestrator(config, storage=storage).run(run_id="unit-test-run")
            self.assertEqual(report["gate"]["verdict"], "PASS")
            self.assertTrue((Path(temp) / "unit-test-run" / "report.html").exists())
            self.assertGreater(report["summary"]["metric_count"], 0)
            self.assertNotIn("pseudo", json.dumps(report).lower())

    def test_disabled_metric_is_not_executed_or_aggregated(self):
        config = load_config(overrides={
            "run": {"max_records": 1, "repeat_count": 1},
            "judge": {"enable_deepeval": False, "enable_ragas": False},
            "target": {"provider": "local-record", "model": "local-record-v1"},
            "metrics": {"enabled": [
                "behavior_compliance",
                "field_accuracy",
                "json_schema_validity",
                "required_fact_coverage",
                "retrieval_document_recall",
                "forbidden_information_leakage",
                "medical_policy_compliance",
                "dangerous_output_absence",
                "cross_patient_non_disclosure",
                "unauthorized_tool_calls",
                "paraphrase_consistency",
                "repeat_run_consistency",
            ]},
        })
        with tempfile.TemporaryDirectory() as temp:
            report = EvaluationOrchestrator(config, storage=RunStorage(Path(temp))).run(run_id="metric-selection-run")
            self.assertNotIn("latency_within_limit", report["aggregates"])
            self.assertNotIn("latency_within_limit", report["manifest"]["enabled_metrics"])


if __name__ == "__main__":
    unittest.main()
