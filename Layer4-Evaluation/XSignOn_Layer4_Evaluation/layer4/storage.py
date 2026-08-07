from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from layer4.config import ROOT
from layer4.utils import read_json, write_json


class RunStorage:
    def __init__(self, reports_root: Path | None = None):
        self.reports_root = reports_root or (ROOT / "reports" / "runs")
        self.reports_root.mkdir(parents=True, exist_ok=True)
        self.state_root = ROOT / "state"
        self.state_root.mkdir(parents=True, exist_ok=True)

    def run_dir(self, run_id: str) -> Path:
        path = self.reports_root / run_id
        path.mkdir(parents=True, exist_ok=True)
        return path

    def save_jsonl(self, path: Path, rows: list[dict[str, Any]]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as handle:
            for row in rows:
                handle.write(json.dumps(row, ensure_ascii=False, default=str) + "\n")

    def save_run(
        self,
        run_id: str,
        config: dict[str, Any],
        cases: list[dict[str, Any]],
        traces: list[dict[str, Any]],
        metrics: list[dict[str, Any]],
        report: dict[str, Any],
        html: str,
    ) -> Path:
        directory = self.run_dir(run_id)
        write_json(directory / "config.json", config)
        self.save_jsonl(directory / "cases.jsonl", cases)
        self.save_jsonl(directory / "traces.jsonl", traces)
        self.save_jsonl(directory / "metrics.jsonl", metrics)
        write_json(directory / "report.json", report)
        (directory / "report.html").write_text(html, encoding="utf-8")
        return directory

    def load_report(self, run_id: str) -> dict[str, Any] | None:
        return read_json(self.reports_root / run_id / "report.json")

    def list_runs(self) -> list[dict[str, Any]]:
        runs: list[dict[str, Any]] = []
        for directory in sorted(self.reports_root.iterdir(), reverse=True):
            if not directory.is_dir():
                continue
            report = read_json(directory / "report.json")
            if report:
                runs.append({
                    "run_id": report.get("run_id", directory.name),
                    "created_at": report.get("created_at"),
                    "verdict": report.get("gate", {}).get("verdict"),
                    "target": report.get("manifest", {}).get("target_model"),
                    "case_count": report.get("summary", {}).get("case_count"),
                })
        return runs

    def set_baseline(self, run_id: str) -> None:
        if not self.load_report(run_id):
            raise FileNotFoundError(f"Run not found: {run_id}")
        write_json(self.state_root / "baseline.json", {"run_id": run_id})

    def get_baseline_report(self) -> dict[str, Any] | None:
        baseline = read_json(self.state_root / "baseline.json")
        return self.load_report(baseline["run_id"]) if baseline and baseline.get("run_id") else None

    def get_baseline_id(self) -> str | None:
        baseline = read_json(self.state_root / "baseline.json")
        return baseline.get("run_id") if baseline else None
