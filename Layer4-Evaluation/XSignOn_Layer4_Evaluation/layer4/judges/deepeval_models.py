from __future__ import annotations

import json
import os
import urllib.request
from typing import Any

try:
    from pydantic import BaseModel
except ImportError:  # pragma: no cover
    BaseModel = Any  # type: ignore

try:
    from deepeval.models.base_model import DeepEvalBaseLLM
except ImportError:  # Allows core mode to import without DeepEval.
    class DeepEvalBaseLLM:  # type: ignore
        pass


class GeminiDeepEvalModel(DeepEvalBaseLLM):
    def __init__(self, model: str, api_key_env: str = "GEMINI_API_KEY"):
        self.model = model
        api_key = os.getenv(api_key_env, "")
        if not api_key:
            raise RuntimeError(f"{api_key_env} is not set")
        try:
            from google import genai
        except ImportError as exc:
            raise RuntimeError("google-genai is not installed") from exc
        self.client = genai.Client(api_key=api_key)

    def load_model(self):
        return self.client

    def get_model_name(self) -> str:
        return f"Gemini:{self.model}"

    def generate(self, prompt: str, schema: type[BaseModel] | None = None):
        from google.genai import types
        config_kwargs: dict[str, Any] = {"max_output_tokens": 3000}
        if schema is not None:
            config_kwargs["response_format"] = {
                "text": {"mime_type": "application/json", "schema": schema.model_json_schema()}
            }
        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt,
                config=types.GenerateContentConfig(**config_kwargs),
            )
        except TypeError:
            fallback: dict[str, Any] = {"max_output_tokens": 3000}
            if schema is not None:
                fallback.update({
                    "response_mime_type": "application/json",
                    "response_json_schema": schema.model_json_schema(),
                })
            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt,
                config=types.GenerateContentConfig(**fallback),
            )
        text = response.text or ""
        return schema.model_validate_json(text) if schema is not None else text

    async def a_generate(self, prompt: str, schema: type[BaseModel] | None = None):
        return self.generate(prompt, schema)


class OllamaDeepEvalModel(DeepEvalBaseLLM):
    def __init__(self, model: str, base_url: str = "http://localhost:11434"):
        self.model = model
        self.base_url = base_url.rstrip("/")

    def load_model(self):
        return self.base_url

    def get_model_name(self) -> str:
        return f"Ollama:{self.model}"

    def generate(self, prompt: str, schema: type[BaseModel] | None = None):
        payload: dict[str, Any] = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0},
        }
        if schema is not None:
            payload["format"] = schema.model_json_schema()
        request = urllib.request.Request(
            f"{self.base_url}/api/generate",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=180) as response:
            body = json.loads(response.read().decode("utf-8"))
        text = body.get("response", "")
        return schema.model_validate_json(text) if schema is not None else text

    async def a_generate(self, prompt: str, schema: type[BaseModel] | None = None):
        return self.generate(prompt, schema)
