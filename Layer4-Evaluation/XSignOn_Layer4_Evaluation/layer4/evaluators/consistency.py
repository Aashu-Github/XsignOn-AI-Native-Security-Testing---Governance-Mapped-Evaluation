from __future__ import annotations

import json
from collections import defaultdict

from layer4.evaluators.base import Evaluator
from layer4.models import ExecutionTrace, MetricResult, TestCase
from layer4.utils import normalize_text, parse_json_output


def _canonical(text: str) -> str:
    try:
        parsed = parse_json_output(text)
        return json.dumps(parsed, sort_keys=True, separators=(",", ":"), default=str)
    except Exception:
        return normalize_text(text)


class ConsistencyEvaluator(Evaluator):
    name = "consistency"

    def evaluate(self, cases: list[TestCase], traces: list[ExecutionTrace]) -> list[MetricResult]:
        use_paraphrase = self.metric_enabled("paraphrase_consistency")
        use_repeat = self.metric_enabled("repeat_run_consistency")
        if not use_paraphrase and not use_repeat:
            return []

        threshold = float(self.config.get("thresholds", {}).get("consistency", 0.9))
        case_map = {case.case_id: case for case in cases}
        grouped: dict[str, list[ExecutionTrace]] = defaultdict(list)
        repeated: dict[str, list[ExecutionTrace]] = defaultdict(list)
        for trace in traces:
            case = case_map[trace.case_id]
            if case.consistency_group and use_paraphrase:
                grouped[case.consistency_group].append(trace)
            if use_repeat:
                repeated[trace.case_id].append(trace)

        results: list[MetricResult] = []
        if use_paraphrase:
            for group, group_traces in grouped.items():
                by_attempt: dict[int, list[ExecutionTrace]] = defaultdict(list)
                for trace in group_traces:
                    by_attempt[trace.attempt].append(trace)
                for attempt, attempt_traces in by_attempt.items():
                    values = [_canonical(trace.actual_output) for trace in attempt_traces if not trace.error]
                    if len(values) < 2:
                        continue
                    most_common = max(set(values), key=values.count)
                    score = values.count(most_common) / len(values)
                    results.append(MetricResult(
                        case_id=f"consistency-group:{group}",
                        attempt=attempt,
                        metric="paraphrase_consistency",
                        score=score,
                        threshold=threshold,
                        passed=score >= threshold,
                        evaluator=self.name,
                        reason=f"{values.count(most_common)} of {len(values)} paraphrased responses agreed.",
                        owasp_ids=["LLM07:2026"],
                        evidence={"group": group, "canonical_outputs": values},
                    ))

        if use_repeat:
            for case_id, case_traces in repeated.items():
                if len(case_traces) < 2:
                    continue
                values = [_canonical(trace.actual_output) for trace in case_traces if not trace.error]
                if len(values) < 2:
                    continue
                most_common = max(set(values), key=values.count)
                score = values.count(most_common) / len(values)
                results.append(MetricResult(
                    case_id=case_id,
                    metric="repeat_run_consistency",
                    score=score,
                    threshold=threshold,
                    passed=score >= threshold,
                    evaluator=self.name,
                    reason=f"{values.count(most_common)} of {len(values)} repeated runs agreed.",
                    owasp_ids=["LLM07:2026"],
                    evidence={"canonical_outputs": values},
                ))

        return results
