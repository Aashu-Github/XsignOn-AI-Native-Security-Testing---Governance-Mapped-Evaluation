from __future__ import annotations

import os
import sys
import types
from typing import Any

from layer4.evaluators.base import Evaluator
from layer4.models import ExecutionTrace, MetricResult, TestCase


def _install_ragas_vertexai_compat() -> None:
    """Bridge RAGAS 0.4.3's legacy LangChain VertexAI import on modern installs.

    RAGAS 0.4.3 imports ``langchain_community.chat_models.vertexai.ChatVertexAI``.
    Recent LangChain releases moved that class to ``langchain_google_vertexai``.
    This alias is installed only when the legacy module is absent, so it does
    not override a real compatibility module if one is already available.
    """
    legacy_module = "langchain_community.chat_models.vertexai"
    try:
        __import__(legacy_module)
        return
    except ImportError:
        pass

    try:
        from langchain_google_vertexai import ChatVertexAI
    except ImportError:
        return

    shim = types.ModuleType(legacy_module)
    shim.ChatVertexAI = ChatVertexAI
    sys.modules[legacy_module] = shim


class RagasEvaluator(Evaluator):
    name = "ragas"

    @staticmethod
    def _result_parts(result: Any) -> tuple[float, str]:
        value = float(getattr(result, "value", result))
        reason = str(getattr(result, "reason", getattr(result, "explanation", "RAGAS completed.")))
        return value, reason

    def _llm(self):
        judge = self.config.get("judge", {})
        provider = str(judge.get("provider", "gemini")).lower()
        model = judge.get("model") or os.getenv("JUDGE_MODEL", "gemini-3.6-flash")
        from ragas.llms import llm_factory

        if provider == "gemini":
            try:
                from google import genai
            except ImportError as exc:
                raise RuntimeError("google-genai is required for the Gemini RAGAS judge") from exc
            api_key = os.getenv(judge.get("api_key_env", "GEMINI_API_KEY"), "")
            if not api_key:
                raise RuntimeError("GEMINI_API_KEY is not set")
            client = genai.Client(api_key=api_key)
            return llm_factory(model, provider="google", client=client)
        if provider == "ollama":
            from openai import AsyncOpenAI
            client = AsyncOpenAI(
                api_key="ollama",
                base_url=judge.get("openai_base_url", "http://localhost:11434/v1"),
                timeout=180.0,
                max_retries=2,
            )
            return llm_factory(model, provider="openai", client=client)
        if provider == "openai-default":
            from openai import AsyncOpenAI
            client = AsyncOpenAI(
                api_key=os.getenv("OPENAI_API_KEY"),
                timeout=180.0,
                max_retries=2,
            )
            return llm_factory(model, provider="openai", client=client)
        raise RuntimeError(f"Unsupported RAGAS judge provider: {provider}")

    def evaluate(self, cases: list[TestCase], traces: list[ExecutionTrace]) -> list[MetricResult]:
        if not self.config.get("judge", {}).get("enable_ragas", False):
            return []

        _install_ragas_vertexai_compat()
        try:
            from ragas.metrics.collections import ContextPrecision, ContextRecall, Faithfulness
        except ImportError as exc:
            return [MetricResult(
                case_id="__run__",
                metric="ragas_available",
                score=0.0,
                threshold=1.0,
                passed=False,
                evaluator=self.name,
                reason="RAGAS could not be imported. Install requirements-full.txt and verify the LangChain compatibility dependency.",
                severity="critical",
                error=str(exc),
            )]

        try:
            llm = self._llm()
        except Exception as exc:
            return [MetricResult(
                case_id="__run__",
                metric="ragas_judge_available",
                score=0.0,
                threshold=1.0,
                passed=False,
                evaluator=self.name,
                reason="RAGAS judge initialization failed.",
                severity="critical",
                error=f"{type(exc).__name__}: {exc}",
            )]

        threshold = float(self.config.get("thresholds", {}).get("ragas", 0.8))
        max_cases = int(self.config.get("judge", {}).get("max_cases", 12))
        case_map = {case.case_id: case for case in cases}
        candidates = [
            trace for trace in traces
            if trace.retrieved_contexts and not trace.error and case_map[trace.case_id].expected_behavior == "answer"
        ][:max_cases]
        results: list[MetricResult] = []

        for trace in candidates:
            case = case_map[trace.case_id]
            contexts = [chunk.text for chunk in trace.retrieved_contexts]
            metric_calls: list[tuple[str, Any, dict[str, Any]]] = [
                (
                    "ragas_faithfulness",
                    Faithfulness(llm=llm),
                    {"user_input": case.input, "response": trace.actual_output, "retrieved_contexts": contexts},
                )
            ]
            if case.reference:
                metric_calls.extend([
                    (
                        "ragas_context_precision",
                        ContextPrecision(llm=llm),
                        {"user_input": case.input, "reference": case.reference, "retrieved_contexts": contexts},
                    ),
                    (
                        "ragas_context_recall",
                        ContextRecall(llm=llm),
                        {"user_input": case.input, "reference": case.reference, "retrieved_contexts": contexts},
                    ),
                ])

            for metric_name, scorer, kwargs in metric_calls:
                try:
                    metric_result = scorer.score(**kwargs)
                    score, reason = self._result_parts(metric_result)
                    passed = score >= threshold
                    error = None
                except Exception as exc:
                    score = None
                    reason = "RAGAS metric failed; no fallback score was generated."
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
                    owasp_ids=["LLM07:2026", "LLM09:2026"],
                    error=error,
                ))

        return results
