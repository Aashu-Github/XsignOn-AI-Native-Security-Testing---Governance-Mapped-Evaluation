from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from layer4.models import ExecutionTrace, TestCase


class TargetError(RuntimeError):
    pass


class TargetAdapter(ABC):
    provider: str
    model: str

    def __init__(self, config: dict[str, Any]):
        self.config = config
        self.provider = str(config.get("provider", "unknown"))
        self.model = str(config.get("model", "unknown"))

    @abstractmethod
    def execute(self, run_id: str, case: TestCase, attempt: int = 1) -> ExecutionTrace:
        raise NotImplementedError
