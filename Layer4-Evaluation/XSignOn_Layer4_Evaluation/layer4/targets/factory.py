from __future__ import annotations

from typing import Any

from layer4.targets.base import TargetAdapter, TargetError
from layer4.targets.gemini import GeminiTarget
from layer4.targets.local_record import LocalRecordTarget
from layer4.targets.ollama import OllamaTarget
from layer4.targets.trace_file import TraceFileTarget


def create_target(config: dict[str, Any]) -> TargetAdapter:
    provider = str(config.get("provider", "local-record")).lower()
    if provider == "local-record":
        return LocalRecordTarget(config)
    if provider == "gemini":
        return GeminiTarget(config)
    if provider == "ollama":
        return OllamaTarget(config)
    if provider == "trace-file":
        return TraceFileTarget(config)
    raise TargetError(f"Unsupported target provider: {provider}")
