from __future__ import annotations

import json
import time
from typing import Any

from layer4.models import ExecutionTrace, TestCase
from layer4.targets.base import TargetAdapter
from layer4.targets.prompting import SYSTEM_PROMPT_VERSION


REFUSAL = "I cannot comply with that request because it violates the evaluation policy."
LIMIT = "The request exceeds the configured safe processing limit and was not expanded."


class LocalRecordTarget(TargetAdapter):
    """Reference implementation that derives every response from the supplied record context.

    This is not a mock scorer. It is a deterministic target application used to verify that the
    evaluation pipeline works before connecting a real LLM or upstream layers.
    """

    def __init__(self, config: dict[str, Any]):
        super().__init__(config)
        self.provider = "local-record"
        self.model = config.get("model", "local-record-v1")

    @staticmethod
    def _record(case: TestCase) -> dict[str, Any]:
        if not case.retrieved_contexts:
            return {}
        return json.loads(case.retrieved_contexts[0].text)

    def execute(self, run_id: str, case: TestCase, attempt: int = 1) -> ExecutionTrace:
        started = time.perf_counter()
        try:
            record = self._record(case)
            if case.expected_behavior == "refuse":
                output = REFUSAL
            elif case.expected_behavior == "limit" or len(case.input) > int(self.config.get("max_input_characters", 20_000)):
                output = LIMIT
            elif case.case_type == "missing_data":
                output = json.dumps({
                    "patient_id": record.get("patient_id"),
                    "bmi": record.get("bmi"),
                    "note": "BMI is not recorded in the supplied record." if record.get("bmi") is None else "BMI is recorded.",
                })
            elif case.case_type == "summary":
                bmi = "not recorded" if record.get("bmi") is None else str(record.get("bmi"))
                output = (
                    f"Patient {record.get('patient_id')} is age {record.get('age')}, with hypertension "
                    f"recorded as {record.get('hypertension')} and heart disease recorded as {record.get('heart_disease')}. "
                    f"Average glucose is {record.get('avg_glucose_level')}, BMI is {bmi}, and smoking status is "
                    f"{record.get('smoking_status')}; this is a record summary, not a diagnosis."
                )
            elif case.response_format == "json":
                fields = case.metadata.get("requested_fields") or list((case.expected_output or {}).keys())
                output = json.dumps({field: record.get(field) for field in fields}, ensure_ascii=False, sort_keys=True)
            else:
                output = "The request was processed using only the supplied record."
            error = None
        except Exception as exc:  # pragma: no cover - defensive boundary
            output = ""
            error = f"{type(exc).__name__}: {exc}"

        elapsed = (time.perf_counter() - started) * 1000
        return ExecutionTrace(
            run_id=run_id,
            case_id=case.case_id,
            attempt=attempt,
            actual_output=output,
            retrieved_contexts=case.retrieved_contexts,
            target_provider=self.provider,
            target_model=self.model,
            model_version="1.0",
            prompt_version=SYSTEM_PROMPT_VERSION,
            latency_ms=elapsed,
            input_tokens=max(1, len(case.input) // 4),
            output_tokens=max(1, len(output) // 4) if output else 0,
            error=error,
            metadata={"reference_target": True},
        )
