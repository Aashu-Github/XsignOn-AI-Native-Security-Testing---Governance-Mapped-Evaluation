from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from layer4.models import ContextChunk, ExecutionTrace, TestCase
from layer4.targets.base import TargetAdapter, TargetError


class TraceFileTarget(TargetAdapter):
    """Loads pre-existing traces from JSONL for future integration with Layers 2/3."""

    def __init__(self, config: dict[str, Any]):
        super().__init__(config)
        self.provider = "trace-file"
        self.model = config.get("model", "upstream-trace")
        path = Path(config.get("trace_file", "data/incoming_traces.jsonl"))
        if not path.is_absolute():
            path = Path(__file__).resolve().parents[2] / path
        if not path.exists():
            raise TargetError(f"Trace file not found: {path}")
        self.rows: dict[tuple[str, int], dict[str, Any]] = {}
        with path.open("r", encoding="utf-8") as handle:
            for line in handle:
                if line.strip():
                    row = json.loads(line)
                    self.rows[(row["case_id"], int(row.get("attempt", 1)))] = row

    def execute(self, run_id: str, case: TestCase, attempt: int = 1) -> ExecutionTrace:
        row = self.rows.get((case.case_id, attempt)) or self.rows.get((case.case_id, 1))
        if not row:
            return ExecutionTrace(
                run_id=run_id,
                case_id=case.case_id,
                attempt=attempt,
                actual_output="",
                retrieved_contexts=[],
                target_provider=self.provider,
                target_model=self.model,
                error=f"No trace found for {case.case_id}",
            )
        contexts = [ContextChunk(**item) for item in row.get("retrieved_contexts", [])]
        return ExecutionTrace(
            run_id=run_id,
            case_id=case.case_id,
            attempt=attempt,
            actual_output=row.get("actual_output", ""),
            retrieved_contexts=contexts,
            target_provider=row.get("target_provider", self.provider),
            target_model=row.get("target_model", self.model),
            model_version=row.get("model_version"),
            prompt_version=row.get("prompt_version", "upstream"),
            retriever_version=row.get("retriever_version", "upstream"),
            latency_ms=float(row.get("latency_ms", 0.0)),
            input_tokens=row.get("input_tokens"),
            output_tokens=row.get("output_tokens"),
            tool_calls=row.get("tool_calls", []),
            error=row.get("error"),
            metadata=row.get("metadata", {}),
        )
