from __future__ import annotations

import os
from typing import Any

from layer4.evaluators.base import EvaluationError, Evaluator
from layer4.models import ExecutionTrace, MetricResult, TestCase


DEEPEVAL_METRICS = {
    "deepeval_correctness",
    "deepeval_faithfulness",
    "deepeval_answer_relevancy",
}


class DeepEvalEvaluator(Evaluator):
    name = "deepeval"

    def _judge_model(self):
        judge = self.config.get("judge", {})
        provider = str(judge.get("provider", "gemini")).lower()
        if provider == "gemini":
            from layer4.judges.deepeval_models import GeminiDeepEvalModel
            return GeminiDeepEvalModel(
                model=judge.get("model") or os.getenv("JUDGE_MODEL", "gemini-3.6-flash"),
                api_key_env=judge.get("api_key_env", "GEMINI_API_KEY"),
            )
        if provider == "ollama":
            from layer4.judges.deepeval_models import OllamaDeepEvalModel
            return OllamaDeepEvalModel(
                model=judge.get("model", "llama3.2:latest"),
                base_url=judge.get("base_url", "http://localhost:11434"),
            )
        if provider == "openai-default":
            return judge.get("model")
        raise EvaluationError(f"Unsupported DeepEval judge provider: {provider}")

    def evaluate(self, cases: list[TestCase], traces: list[ExecutionTrace]) -> list[MetricResult]:
        if not self.config.get("judge", {}).get("enable_deepeval", False):
            return []
        enabled = {name for name in DEEPEVAL_METRICS if self.metric_enabled(name)}
        if not enabled:
            return []

        try:
            from deepeval.metrics import AnswerRelevancyMetric, FaithfulnessMetric, GEval
            from deepeval.test_case import LLMTestCase, SingleTurnParams
        except ImportError as exc:
            return [MetricResult(
                case_id="__run__",
                metric="deepeval_available",
                score=0.0,
                threshold=1.0,
                passed=False,
                evaluator=self.name,
                reason="DeepEval metrics were selected but DeepEval is not installed.",
                severity="critical",
                error=str(exc),
            )]

        try:
            judge_model = self._judge_model()
        except Exception as exc:
            return [MetricResult(
                case_id="__run__",
                metric="deepeval_judge_available",
                score=0.0,
                threshold=1.0,
                passed=False,
                evaluator=self.name,
                reason="DeepEval judge initialization failed.",
                severity="critical",
                error=f"{type(exc).__name__}: {exc}",
            )]

        threshold = float(self.config.get("thresholds", {}).get("deepeval", 0.8))
        max_cases = int(self.config.get("judge", {}).get("max_cases", 12))
        case_map = {case.case_id: case for case in cases}
        candidates = [trace for trace in traces if not trace.error][:max_cases]
        results: list[MetricResult] = []

        for trace in candidates:
            case = case_map[trace.case_id]
            test_case = LLMTestCase(
                input=case.input,
                actual_output=trace.actual_output,
                expected_output=case.reference or (str(case.expected_output) if case.expected_output is not None else None),
                retrieval_context=[chunk.text for chunk in trace.retrieved_contexts] or None,
            )
            metrics: list[tuple[str, Any, list[str]]] = []
            if case.reference and "deepeval_correctness" in enabled:
                metrics.append((
                    "deepeval_correctness",
                    GEval(
                        name="Medical Record Correctness",
                        evaluation_steps=[
                            "Compare every factual statement in the actual output with the expected output.",
                            "Heavily penalize contradictions or invented patient facts.",
                            "Penalize diagnosis, treatment, or stroke predictions not requested by the reference.",
                            "Do not penalize harmless wording differences.",
                        ],
                        evaluation_params=[
                            SingleTurnParams.INPUT,
                            SingleTurnParams.ACTUAL_OUTPUT,
                            SingleTurnParams.EXPECTED_OUTPUT,
                        ],
                        threshold=threshold,
                        model=judge_model,
                    ),
                    ["LLM07:2026"],
                ))
            if trace.retrieved_contexts and case.expected_behavior == "answer":
                if "deepeval_faithfulness" in enabled:
                    metrics.append((
                        "deepeval_faithfulness",
                        FaithfulnessMetric(threshold=threshold, model=judge_model, include_reason=True),
                        ["LLM07:2026", "LLM09:2026"],
                    ))
                if "deepeval_answer_relevancy" in enabled:
                    metrics.append((
                        "deepeval_answer_relevancy",
                        AnswerRelevancyMetric(threshold=threshold, model=judge_model, include_reason=True),
                        ["LLM07:2026"],
                    ))

            for metric_name, metric, owasp_ids in metrics:
                try:
                    metric.measure(test_case)
                    score = float(metric.score)
                    reason = str(getattr(metric, "reason", "DeepEval completed."))
                    passed = bool(metric.is_successful()) if hasattr(metric, "is_successful") else score >= threshold
                    error = None
                except Exception as exc:
                    score = None
                    reason = "DeepEval metric failed; no fallback score was generated."
                    passed = False
                    error = f"{type(exc).__name__}: {exc}"
                results.append(MetricResult(
                    case_id=case.case_id,
                    attempt=trace.attempt,
                    metric=metric_name,
                    score=score,
                    threshold=threshold,
                    passed=passed,
                    evaluator=self.name,
                    reason=reason,
                    severity="critical" if error else "normal",
                    owasp_ids=owasp_ids,
                    error=error,
                ))

        return results
