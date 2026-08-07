from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class ContextChunk:
    document_id: str
    text: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class TestCase:
    case_id: str
    case_type: str
    input: str
    expected_output: Any = None
    reference: str | None = None
    retrieved_contexts: list[ContextChunk] = field(default_factory=list)
    reference_document_ids: list[str] = field(default_factory=list)
    expected_behavior: str = "answer"
    response_format: str = "text"
    authorized_patient_id: str | None = None
    target_patient_id: str | None = None
    owasp_ids: list[str] = field(default_factory=list)
    policy_ids: list[str] = field(default_factory=list)
    consistency_group: str | None = None
    forbidden_strings: list[str] = field(default_factory=list)
    required_facts: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TestCase":
        contexts = [ContextChunk(**item) for item in data.get("retrieved_contexts", [])]
        payload = dict(data)
        payload["retrieved_contexts"] = contexts
        return cls(**payload)


@dataclass
class ExecutionTrace:
    run_id: str
    case_id: str
    attempt: int
    actual_output: str
    retrieved_contexts: list[ContextChunk]
    target_provider: str
    target_model: str
    model_version: str | None = None
    prompt_version: str = "medical-assistant-v1"
    retriever_version: str = "in-memory-record-retriever-v1"
    latency_ms: float = 0.0
    input_tokens: int | None = None
    output_tokens: int | None = None
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class MetricResult:
    case_id: str
    metric: str
    score: float | None
    threshold: float | None
    passed: bool | None
    evaluator: str
    reason: str
    attempt: int = 1
    severity: str = "normal"
    owasp_ids: list[str] = field(default_factory=list)
    evidence: dict[str, Any] = field(default_factory=dict)
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
