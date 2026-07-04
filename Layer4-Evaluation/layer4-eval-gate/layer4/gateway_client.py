from __future__ import annotations

import copy
import json
from typing import Any

import requests

from layer4.config import TargetConfig


def _get_by_path(obj: Any, dotted_path: str) -> Any:
    """Walk a dotted path like 'choices.0.message.content' through dicts/lists."""
    current = obj
    for part in dotted_path.split("."):
        if isinstance(current, list):
            current = current[int(part)]
        elif isinstance(current, dict):
            current = current[part]
        else:
            raise KeyError(f"Cannot descend into '{part}' of {type(current)}")
    return current


def _fill_template(template: dict, input_text: str) -> dict:
    """Recursively substitute '{input}' in a request template with the probe text."""
    filled = copy.deepcopy(template)

    def walk(node):
        if isinstance(node, dict):
            return {k: walk(v) for k, v in node.items()}
        if isinstance(node, list):
            return [walk(v) for v in node]
        if isinstance(node, str):
            return node.replace("{input}", input_text)
        return node

    return walk(filled)


class GatewayClient:
    """Sends a probe input to a real target through the Layer 1 gateway and
    extracts the model's answer (and retrieved context, for RAG targets).

    This is intentionally a thin, swappable HTTP client. If your gateway
    uses auth headers, streaming, or a different transport, this is the
    only file you should need to touch.
    """

    def __init__(self, target: TargetConfig, timeout: float = 60.0, extra_headers: dict | None = None):
        self.target = target
        self.timeout = timeout
        self.headers = {"Content-Type": "application/json"}
        if extra_headers:
            self.headers.update(extra_headers)

    def query(self, input_text: str) -> dict:
        """Returns {"actual_output": str, "retrieval_context": list[str] | None}."""
        body = _fill_template(self.target.request_template, input_text)
        resp = requests.post(
            self.target.endpoint,
            headers=self.headers,
            data=json.dumps(body),
            timeout=self.timeout,
        )
        resp.raise_for_status()
        payload = resp.json()

        actual_output = _get_by_path(payload, self.target.response_path)

        retrieval_context = None
        if self.target.is_rag and self.target.context_path:
            retrieval_context = _get_by_path(payload, self.target.context_path)
            if isinstance(retrieval_context, str):
                retrieval_context = [retrieval_context]

        return {"actual_output": actual_output, "retrieval_context": retrieval_context}
