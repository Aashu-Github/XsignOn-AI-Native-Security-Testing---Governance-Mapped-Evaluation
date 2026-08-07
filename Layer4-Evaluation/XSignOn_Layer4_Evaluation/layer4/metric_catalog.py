from __future__ import annotations

from typing import Any

# These are user-selectable evaluation metrics. Technical integrity checks such as
# target_execution and judge/library availability remain mandatory and cannot be disabled.
METRIC_CATALOG: list[dict[str, Any]] = [
    {
        "id": "behavior_compliance",
        "label": "Behavior compliance",
        "group": "Core behavior",
        "description": "Checks whether the model refused or limited a request when the test case required it.",
    },
    {
        "id": "field_accuracy",
        "label": "Field accuracy",
        "group": "Correctness",
        "description": "Compares structured JSON fields with the expected values generated from the source record.",
    },
    {
        "id": "json_schema_validity",
        "label": "JSON schema validity",
        "group": "Correctness",
        "description": "Checks that JSON-required responses can be parsed as a JSON object.",
    },
    {
        "id": "required_fact_coverage",
        "label": "Required fact coverage",
        "group": "Correctness",
        "description": "Measures how many required source-record facts appear in a summary response.",
    },
    {
        "id": "retrieval_document_recall",
        "label": "Retrieval document recall",
        "group": "Grounding",
        "description": "Checks whether the execution trace contains the document IDs required by the test case.",
    },
    {
        "id": "latency_within_limit",
        "label": "Latency within limit",
        "group": "Performance",
        "description": "Checks each target response against the configured latency limit.",
    },
    {
        "id": "forbidden_information_leakage",
        "label": "Forbidden information leakage",
        "group": "Safety",
        "description": "Detects protected canaries, private values, and secrets that must not appear in output.",
    },
    {
        "id": "medical_policy_compliance",
        "label": "Medical policy compliance",
        "group": "Safety",
        "description": "Detects prohibited diagnosis or prescription language in applicable medical test cases.",
    },
    {
        "id": "dangerous_output_absence",
        "label": "Dangerous output absence",
        "group": "Safety",
        "description": "Checks that the model did not emit dangerous executable commands, SQL, or script payloads.",
    },
    {
        "id": "cross_patient_non_disclosure",
        "label": "Cross-patient non-disclosure",
        "group": "Privacy",
        "description": "Checks that a protected patient identifier was not disclosed in a cross-patient request.",
    },
    {
        "id": "unauthorized_tool_calls",
        "label": "Unauthorized tool calls",
        "group": "Agency",
        "description": "Checks execution traces for tool calls that were not explicitly authorized.",
    },
    {
        "id": "paraphrase_consistency",
        "label": "Paraphrase consistency",
        "group": "Consistency",
        "description": "Compares answers to different phrasings of the same underlying question.",
    },
    {
        "id": "repeat_run_consistency",
        "label": "Repeat-run consistency",
        "group": "Consistency",
        "description": "Compares repeated executions of the same test case.",
    },
    {
        "id": "deepeval_correctness",
        "label": "DeepEval correctness",
        "group": "DeepEval",
        "description": "Uses DeepEval GEval and the selected judge model to compare the answer with its reference.",
        "requires": "deepeval",
    },
    {
        "id": "deepeval_faithfulness",
        "label": "DeepEval faithfulness",
        "group": "DeepEval",
        "description": "Uses DeepEval to judge whether claims are supported by the retrieved context.",
        "requires": "deepeval",
    },
    {
        "id": "deepeval_answer_relevancy",
        "label": "DeepEval answer relevancy",
        "group": "DeepEval",
        "description": "Uses DeepEval to judge whether the response directly answers the user question.",
        "requires": "deepeval",
    },
    {
        "id": "ragas_faithfulness",
        "label": "RAGAS faithfulness",
        "group": "RAGAS",
        "description": "Uses RAGAS to judge whether response claims are supported by retrieved context.",
        "requires": "ragas",
    },
    {
        "id": "ragas_context_precision",
        "label": "RAGAS context precision",
        "group": "RAGAS",
        "description": "Uses RAGAS to assess whether the supplied context is relevant to the reference answer.",
        "requires": "ragas",
    },
    {
        "id": "ragas_context_recall",
        "label": "RAGAS context recall",
        "group": "RAGAS",
        "description": "Uses RAGAS to assess whether the context contains the information needed by the reference answer.",
        "requires": "ragas",
    },
]

METRIC_IDS = {item["id"] for item in METRIC_CATALOG}
DEFAULT_ENABLED_METRICS = [item["id"] for item in METRIC_CATALOG]


def normalize_enabled_metrics(value: Any) -> list[str]:
    """Return a de-duplicated, catalog-ordered list of enabled metric IDs."""
    if value is None:
        return list(DEFAULT_ENABLED_METRICS)
    if not isinstance(value, list):
        raise ValueError("enabled_metrics must be an array of metric IDs")
    requested = {str(item) for item in value}
    unknown = sorted(requested - METRIC_IDS)
    if unknown:
        raise ValueError(f"Unknown metric(s): {', '.join(unknown)}")
    return [metric_id for metric_id in DEFAULT_ENABLED_METRICS if metric_id in requested]
