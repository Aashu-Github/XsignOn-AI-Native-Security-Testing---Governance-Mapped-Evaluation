from __future__ import annotations

import csv
import math
from pathlib import Path
from typing import Any


def _rank(values: list[float]) -> list[float]:
    ordered = sorted(enumerate(values), key=lambda item: item[1])
    ranks = [0.0] * len(values)
    i = 0
    while i < len(ordered):
        j = i
        while j + 1 < len(ordered) and ordered[j + 1][1] == ordered[i][1]:
            j += 1
        average_rank = (i + j + 2) / 2
        for k in range(i, j + 1):
            ranks[ordered[k][0]] = average_rank
        i = j + 1
    return ranks


def _pearson(a: list[float], b: list[float]) -> float | None:
    if len(a) < 2 or len(a) != len(b):
        return None
    mean_a = sum(a) / len(a)
    mean_b = sum(b) / len(b)
    numerator = sum((x - mean_a) * (y - mean_b) for x, y in zip(a, b))
    denominator = math.sqrt(sum((x - mean_a) ** 2 for x in a) * sum((y - mean_b) ** 2 for y in b))
    return numerator / denominator if denominator else None


def spearman(a: list[float], b: list[float]) -> float | None:
    return _pearson(_rank(a), _rank(b))


def quadratic_weighted_kappa(a: list[int], b: list[int], minimum: int = 1, maximum: int = 5) -> float | None:
    if len(a) < 2 or len(a) != len(b):
        return None
    size = maximum - minimum + 1
    observed = [[0.0] * size for _ in range(size)]
    hist_a = [0.0] * size
    hist_b = [0.0] * size
    for x, y in zip(a, b):
        i, j = x - minimum, y - minimum
        if not (0 <= i < size and 0 <= j < size):
            continue
        observed[i][j] += 1
        hist_a[i] += 1
        hist_b[j] += 1
    total = sum(hist_a)
    if total == 0:
        return None
    weighted_observed = 0.0
    weighted_expected = 0.0
    for i in range(size):
        for j in range(size):
            weight = ((i - j) ** 2) / ((size - 1) ** 2)
            weighted_observed += weight * observed[i][j] / total
            weighted_expected += weight * (hist_a[i] * hist_b[j]) / (total * total)
    return 1 - weighted_observed / weighted_expected if weighted_expected else None


class JudgeCalibration:
    def __init__(self, ratings_path: Path, config: dict[str, Any]):
        self.ratings_path = ratings_path
        self.config = config

    def run(self, metric_rows: list[dict[str, Any]]) -> dict[str, Any]:
        if not self.ratings_path.exists():
            return {"status": "not_run", "reason": "Human ratings file does not exist."}
        human: dict[tuple[str, str], int] = {}
        with self.ratings_path.open("r", encoding="utf-8-sig", newline="") as handle:
            for row in csv.DictReader(handle):
                if row.get("human_rating"):
                    human[(row["case_id"], row["metric"])] = int(row["human_rating"])

        judge_values: list[float] = []
        human_values: list[float] = []
        judge_categories: list[int] = []
        human_categories: list[int] = []
        matched: list[dict[str, Any]] = []
        for row in metric_rows:
            key = (row["case_id"], row["metric"])
            if key not in human or row.get("score") is None or row.get("evaluator") not in {"deepeval", "ragas"}:
                continue
            judge_score = float(row["score"])
            human_rating = human[key]
            judge_rating = max(1, min(5, round(judge_score * 4 + 1)))
            judge_values.append(judge_score)
            human_values.append((human_rating - 1) / 4)
            judge_categories.append(judge_rating)
            human_categories.append(human_rating)
            matched.append({"case_id": key[0], "metric": key[1], "judge_score": judge_score, "human_rating": human_rating})

        if len(matched) < 2:
            return {"status": "not_run", "reason": "Add at least two matching human ratings.", "matched": matched}

        rho = spearman(judge_values, human_values)
        kappa = quadratic_weighted_kappa(judge_categories, human_categories)
        minimum = float(self.config.get("thresholds", {}).get("judge_minimum_kappa", 0.7))
        passed = kappa is not None and kappa >= minimum
        return {
            "status": "pass" if passed else "fail",
            "spearman": rho,
            "weighted_kappa": kappa,
            "minimum_weighted_kappa": minimum,
            "matched": matched,
            "reason": "Judge calibration met the configured agreement threshold." if passed else "Judge calibration did not meet the configured agreement threshold.",
        }
