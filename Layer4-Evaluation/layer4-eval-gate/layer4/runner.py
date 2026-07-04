from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from deepeval.test_case import LLMTestCase

from layer4.config import SuiteConfig, TargetConfig, load_probes
from layer4.gateway_client import GatewayClient
from layer4.owasp_metrics import build_metric
from layer4.ragas_gate import run_ragas
from layer4.report import render_report
from layer4.schema import GateRun, MetricResult


def run_deepeval_gate(suite: SuiteConfig, target: TargetConfig, probes: list[dict], client: GatewayClient) -> list[MetricResult]:
    results: list[MetricResult] = []

    for probe in probes:
        category = probe["category"]
        threshold = suite.threshold_for(category)
        metric = build_metric(category, threshold, suite.deepeval_judge_model)

        response = client.query(probe["input"])

        test_case = LLMTestCase(
            input=probe["input"],
            actual_output=response["actual_output"],
            expected_output=probe.get("expected_behavior", ""),
            retrieval_context=response.get("retrieval_context"),
        )

        metric.measure(test_case)

        results.append(
            MetricResult(
                tool="deepeval",
                category=category,
                label=getattr(metric, "name", category),
                score=float(metric.score),
                threshold=threshold,
                passed=bool(metric.score >= threshold),
                reason=getattr(metric, "reason", None),
                probe_id=probe.get("id"),
            )
        )

    return results


def run_ragas_gate(suite: SuiteConfig, probes: list[dict], client: GatewayClient) -> list[MetricResult]:
    samples = []
    for probe in probes:
        response = client.query(probe["input"])
        contexts = response.get("retrieval_context") or []
        samples.append(
            {
                "question": probe["input"],
                "answer": response["actual_output"],
                "contexts": contexts,
            }
        )

    ragas_result = run_ragas(samples, suite.ragas_fail_under, suite.ragas_judge_model)

    return [
        MetricResult(
            tool="ragas",
            category="LLM02 / LLM09",
            label="faithfulness",
            score=ragas_result.faithfulness,
            threshold=ragas_result.threshold,
            passed=ragas_result.faithfulness >= ragas_result.threshold,
        ),
        MetricResult(
            tool="ragas",
            category="LLM09",
            label="answer relevancy",
            score=ragas_result.answer_relevancy,
            threshold=ragas_result.threshold,
            passed=ragas_result.answer_relevancy >= ragas_result.threshold,
        ),
    ]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Layer 4 CI evaluation gate")
    parser.add_argument("--suite", default="suite.yaml")
    parser.add_argument("--target", default=None, help="override target yaml from suite.yaml")
    parser.add_argument("--dataset", default=None, help="override dataset jsonl from suite.yaml")
    args = parser.parse_args(argv)

    suite = SuiteConfig.load(args.suite)
    target = TargetConfig.load(args.target or suite.target_path)
    probes = load_probes(args.dataset or suite.dataset_path)
    client = GatewayClient(target)

    run = GateRun(target_name=target.name, target_type=target.type, threshold_default=suite.deepeval_fail_under)

    print(f"[layer4] scoring {target.name} ({target.type}) against {len(probes)} probes...")
    run.results.extend(run_deepeval_gate(suite, target, probes, client))

    if target.is_rag:
        print("[layer4] target type=rag -> activating RAGAS")
        run.results.extend(run_ragas_gate(suite, probes, client))
    else:
        print("[layer4] target type != rag -> skipping RAGAS")

    out_dir = Path(suite.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    results_path = out_dir / "results.json"
    results_path.write_text(json.dumps(run.to_dict(), indent=2))

    report_path = render_report(run, out_dir / "report.html")

    print(f"[layer4] wrote {results_path}")
    print(f"[layer4] wrote {report_path}")

    if run.blocked:
        print(f"[layer4] BLOCK MERGE — {len(run.failures)} metric(s) below threshold:")
        for f in run.failures:
            print(f"  - {f.tool}:{f.category} ({f.label}) scored {f.score:.2f} < {f.threshold:.2f}")
        return 1

    print("[layer4] ALLOW MERGE — all metrics at or above threshold")
    return 0


if __name__ == "__main__":
    sys.exit(main())
