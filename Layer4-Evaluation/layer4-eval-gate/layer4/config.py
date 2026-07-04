from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass
class TargetConfig:
    name: str
    type: str  # "chat" | "rag"
    endpoint: str
    model: str
    request_template: dict
    response_path: str
    context_path: str | None = None

    @property
    def is_rag(self) -> bool:
        return self.type == "rag"

    @classmethod
    def load(cls, path: str | Path) -> "TargetConfig":
        data = yaml.safe_load(Path(path).read_text())
        return cls(
            name=data["name"],
            type=data.get("type", "chat"),
            endpoint=data["endpoint"],
            model=data.get("model", data["name"]),
            request_template=data.get("request_template", {}),
            response_path=data["response_path"],
            context_path=data.get("context_path"),
        )


@dataclass
class SuiteConfig:
    deepeval_fail_under: float
    deepeval_judge_model: str
    deepeval_category_overrides: dict[str, float]
    ragas_fail_under: float
    ragas_judge_model: str
    target_path: str
    dataset_path: str
    output_dir: str
    raw: dict = field(default_factory=dict)

    def threshold_for(self, category: str) -> float:
        return self.deepeval_category_overrides.get(category, self.deepeval_fail_under)

    @classmethod
    def load(cls, path: str | Path) -> "SuiteConfig":
        data = yaml.safe_load(Path(path).read_text())
        de = data.get("deepeval", {})
        ra = data.get("ragas", {})
        return cls(
            deepeval_fail_under=float(de.get("fail_under", 0.85)),
            deepeval_judge_model=de.get("judge_model", "gpt-4o-mini"),
            deepeval_category_overrides=de.get("category_overrides", {}) or {},
            ragas_fail_under=float(ra.get("fail_under", 0.85)),
            ragas_judge_model=ra.get("judge_model", "gpt-4o-mini"),
            target_path=data["target"],
            dataset_path=data["dataset"],
            output_dir=data.get("output_dir", "results"),
            raw=data,
        )


def load_probes(path: str | Path) -> list[dict[str, Any]]:
    """Load newline-delimited JSON probe file."""
    probes = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            probes.append(json.loads(line))
    return probes
