from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Any

from layer4.utils import read_json


OWASP_2026 = {
    "LLM01:2026": "Prompt Injection",
    "LLM02:2026": "Sensitive Information Disclosure",
    "LLM03:2026": "Excessive Agency",
    "LLM04:2026": "Supply Chain",
    "LLM05:2026": "Data and Model Poisoning",
    "LLM06:2026": "Unbounded Consumption",
    "LLM07:2026": "Misinformation",
    "LLM08:2026": "Hidden Context Exposure",
    "LLM09:2026": "Vector and Embedding Weaknesses",
    "LLM10:2026": "Improper Output Handling",
}


class OwaspCoverage:
    def __init__(self, evidence_path: Path):
        self.evidence_path = evidence_path

    def build(self, metric_rows: list[dict[str, Any]], traces: list[dict[str, Any]]) -> list[dict[str, Any]]:
        mapped: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for row in metric_rows:
            for oid in row.get("owasp_ids", []):
                mapped[oid].append(row)

        supply_chain = read_json(self.evidence_path, default={}) or {}
        output: list[dict[str, Any]] = []
        for oid, name in OWASP_2026.items():
            evidence = mapped.get(oid, [])
            if oid == "LLM04:2026":
                generated = bool(supply_chain.get("generated_at"))
                status = "manual_review" if generated else "not_evaluated"
                output.append({
                    "id": oid,
                    "name": name,
                    "status": status,
                    "evidence_count": 1 if generated else 0,
                    "reason": (
                        "Software inventory evidence was collected; vulnerability and provenance review remains manual."
                        if generated else "Generate the local SBOM and attach model/dataset provenance evidence."
                    ),
                    "failed_metrics": [],
                })
                continue
            if oid == "LLM03:2026" and not any(trace.get("tool_calls") for trace in traces):
                output.append({
                    "id": oid,
                    "name": name,
                    "status": "not_applicable",
                    "evidence_count": len(evidence),
                    "reason": "The selected target produced no tool calls. Output-safety evidence was collected, but excessive agency requires an agent or tool-enabled target.",
                    "failed_metrics": [],
                })
                continue
            if not evidence:
                status = "not_evaluated"
                reason = "No automated evidence was collected for this category in the current run."
            else:
                failures = [row for row in evidence if row.get("passed") is False]
                status = "fail" if failures else "pass"
                reason = "One or more mapped checks failed." if failures else "All mapped automated checks passed."
            output.append({
                "id": oid,
                "name": name,
                "status": status,
                "evidence_count": len(evidence),
                "reason": reason,
                "failed_metrics": sorted({row["metric"] for row in evidence if row.get("passed") is False}),
            })
        return output
