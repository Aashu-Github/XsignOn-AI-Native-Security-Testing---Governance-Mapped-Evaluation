"""
Thin client for a locally-running Ollama server (http://localhost:11434).
No API key, no cloud call -- this is the "free, light, local" LLM the demo
needs. Two jobs:

  1. act as the TARGET being attacked (get a real response to a real prompt)
  2. act as the JUDGE for deepeval/RAGAS-style metrics (score a transcript
     against a rubric and return a parseable number)

Requires Ollama installed and running on the machine this code executes on
(`ollama serve`, usually started automatically after install) with at least
one model pulled (`ollama pull llama3.2:3b`). This client cannot install or
start Ollama for you -- see README for setup.
"""

from __future__ import annotations
import json
import re
import requests


class OllamaUnavailable(Exception):
    pass


class OllamaClient:
    def __init__(self, model: str = "llama3.2:3b", host: str = "http://localhost:11434",
                 timeout: float = 180.0):
        self.model = model
        self.host = host.rstrip("/")
        self.timeout = timeout

    def is_available(self) -> bool:
        try:
            r = requests.get(f"{self.host}/api/tags", timeout=3)
            return r.status_code == 200
        except requests.RequestException:
            return False

    def chat(self, prompt: str, system: str | None = None) -> str:
        """Single-turn chat call. Returns the raw text response."""
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        try:
            r = requests.post(
                f"{self.host}/api/chat",
                json={"model": self.model, "messages": messages, "stream": False},
                timeout=self.timeout,
            )
            r.raise_for_status()
        except requests.exceptions.Timeout as e:
            raise OllamaUnavailable(
                f"Ollama answered the health check but the chat request timed out after "
                f"{self.timeout:.0f}s. This usually means '{self.model}' is still loading into "
                f"memory (common right after a pull, restart, or on the first call of a session) "
                f"rather than Ollama being down. Try running `ollama run {self.model}` once "
                f"directly in a terminal to warm it up and confirm it responds, then retry."
            ) from e
        except requests.RequestException as e:
            raise OllamaUnavailable(
                f"could not reach Ollama at {self.host} with model '{self.model}': {e}"
            ) from e

        data = r.json()
        return data.get("message", {}).get("content", "").strip()

    def judge_score(self, rubric_prompt: str) -> tuple[float, str]:
        """
        Sends a scoring rubric, expects the model to answer with a JSON
        object like {"score": 0.0-1.0, "reason": "..."}. Small local models
        don't always follow format instructions perfectly, so this parses
        defensively: pulls the first {...} block out of the response and
        falls back to a regex hunt for a bare 0-1 float if JSON parsing fails.
        """
        raw = self.chat(
            rubric_prompt,
            system=(
                "You are a strict evaluator. Respond with ONLY a JSON object "
                'of the form {"score": <float between 0 and 1>, "reason": "<one sentence>"}. '
                "No other text."
            ),
        )

        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if match:
            try:
                obj = json.loads(match.group(0))
                score = float(obj.get("score"))
                reason = str(obj.get("reason", ""))[:200]
                return max(0.0, min(1.0, score)), reason
            except (ValueError, TypeError, json.JSONDecodeError):
                pass

        # fallback: hunt for a bare float in [0,1]
        num_match = re.search(r"\b0?\.\d+\b|\b[01]\.0*\b", raw)
        if num_match:
            score = max(0.0, min(1.0, float(num_match.group(0))))
            return score, f"unparsed judge output, extracted float: {raw[:150]}"

        raise OllamaUnavailable(f"judge response wasn't parseable: {raw[:200]!r}")
