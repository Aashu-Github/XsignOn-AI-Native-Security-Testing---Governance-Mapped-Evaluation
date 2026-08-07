from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from typing import Any

from layer4.models import ExecutionTrace, TestCase
from layer4.targets.base import TargetAdapter, TargetError
from layer4.targets.prompting import SYSTEM_PROMPT, SYSTEM_PROMPT_VERSION, build_user_prompt


class OllamaTarget(TargetAdapter):
    def __init__(self, config: dict[str, Any]):
        super().__init__(config)
        self.provider = "ollama"
        self.model = config.get("model", "llama3.2")
        self.base_url = config.get("base_url", "http://localhost:11434").rstrip("/")

    def execute(self, run_id: str, case: TestCase, attempt: int = 1) -> ExecutionTrace:
        started = time.perf_counter()
        payload: dict[str, Any] = {
            "model": self.model,
            "stream": False,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": build_user_prompt(case)},
            ],
            "options": {"temperature": float(self.config.get("temperature", 0.0))},
        }
        if case.response_format == "json":
            payload["format"] = "json"

        output = ""
        error = None
        input_tokens = None
        output_tokens = None
        try:
            request = urllib.request.Request(
                f"{self.base_url}/api/chat",
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(request, timeout=float(self.config.get("timeout_seconds", 120))) as response:
                body = json.loads(response.read().decode("utf-8"))
            output = body.get("message", {}).get("content", "")
            input_tokens = body.get("prompt_eval_count")
            output_tokens = body.get("eval_count")
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            error = f"{type(exc).__name__}: {exc}"
        except Exception as exc:  # pragma: no cover
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
            prompt_version=SYSTEM_PROMPT_VERSION,
            latency_ms=elapsed,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            error=error,
        )
