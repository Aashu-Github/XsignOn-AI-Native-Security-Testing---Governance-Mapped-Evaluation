from __future__ import annotations

import os
import time
from typing import Any

from layer4.models import ExecutionTrace, TestCase
from layer4.targets.base import TargetAdapter, TargetError
from layer4.targets.prompting import SYSTEM_PROMPT, SYSTEM_PROMPT_VERSION, build_user_prompt


class GeminiTarget(TargetAdapter):
    def __init__(self, config: dict[str, Any]):
        super().__init__(config)
        self.provider = "gemini"
        self.model = config.get("model") or os.getenv("TARGET_MODEL", "gemini-3.6-flash")
        self.api_key = os.getenv(config.get("api_key_env", "GEMINI_API_KEY"), "")
        if not self.api_key:
            raise TargetError("GEMINI_API_KEY is not set. The key is read only from the environment.")
        try:
            from google import genai
        except ImportError as exc:
            raise TargetError("google-genai is not installed. Run: pip install -r requirements-full.txt") from exc
        self.client = genai.Client(api_key=self.api_key)

    @staticmethod
    def _schema_for(case: TestCase) -> dict[str, Any] | None:
        if case.response_format != "json":
            return None
        expected = case.expected_output if isinstance(case.expected_output, dict) else {}
        properties: dict[str, Any] = {}
        required: list[str] = []
        for key, value in expected.items():
            required.append(key)
            if value is None:
                properties[key] = {"type": ["string", "number", "boolean", "null"]}
            elif isinstance(value, bool):
                properties[key] = {"type": "boolean"}
            elif isinstance(value, int):
                properties[key] = {"type": "integer"}
            elif isinstance(value, float):
                properties[key] = {"type": "number"}
            else:
                properties[key] = {"type": "string"}
        return {"type": "object", "properties": properties, "required": required, "additionalProperties": False}

    def execute(self, run_id: str, case: TestCase, attempt: int = 1) -> ExecutionTrace:
        started = time.perf_counter()
        error = None
        output = ""
        input_tokens = None
        output_tokens = None
        try:
            from google.genai import types

            schema = self._schema_for(case)
            config_kwargs: dict[str, Any] = {
                "system_instruction": SYSTEM_PROMPT,
                "max_output_tokens": int(self.config.get("max_output_tokens", 800)),
            }
            if schema:
                # Current Google GenAI SDK structured-output shape.
                config_kwargs["response_format"] = {
                    "text": {"mime_type": "application/json", "schema": schema}
                }
            response = self.client.models.generate_content(
                model=self.model,
                contents=build_user_prompt(case),
                config=types.GenerateContentConfig(**config_kwargs),
            )
            output = response.text or ""
            usage = getattr(response, "usage_metadata", None)
            input_tokens = getattr(usage, "prompt_token_count", None) if usage else None
            output_tokens = getattr(usage, "candidates_token_count", None) if usage else None
        except TypeError:
            # Compatibility fallback for older google-genai releases.
            try:
                from google.genai import types
                schema = self._schema_for(case)
                fallback: dict[str, Any] = {
                    "system_instruction": SYSTEM_PROMPT,
                    "max_output_tokens": int(self.config.get("max_output_tokens", 800)),
                }
                if schema:
                    fallback.update({"response_mime_type": "application/json", "response_json_schema": schema})
                response = self.client.models.generate_content(
                    model=self.model,
                    contents=build_user_prompt(case),
                    config=types.GenerateContentConfig(**fallback),
                )
                output = response.text or ""
            except Exception as exc:
                error = f"{type(exc).__name__}: {exc}"
        except Exception as exc:
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
