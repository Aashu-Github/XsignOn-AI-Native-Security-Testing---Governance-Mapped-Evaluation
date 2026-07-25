"""
Loads YOUR data instead of the canned sample transcripts. JSON and CSV are
interchangeable -- both get normalized into the same shape, so the rest of
the pipeline never has to know which format you used.

Expected fields per row/object (all optional except `seed`):
  id       -- your own identifier, auto-generated if missing
  category -- what kind of attack this is (e.g. "prompt_injection",
              "data_exfiltration"). Defaults to "custom".
  seed     -- the idea/topic/prompt to build a test from. Also accepts
              `prompt` or `text` as column/key names.

JSON: either a plain list of objects, or {"seeds": [...]}.
CSV: a header row with any of the column names above.
"""

from __future__ import annotations
import csv
import json
from pathlib import Path


def load_input_file(path: str) -> list[dict]:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"input file not found: {path}")

    suffix = p.suffix.lower()
    if suffix == ".json":
        raw = json.loads(p.read_text())
        items = raw if isinstance(raw, list) else raw.get("seeds", [])
    elif suffix == ".csv":
        with open(p, newline="") as f:
            items = list(csv.DictReader(f))
    else:
        raise ValueError(f"unsupported input file type '{suffix}' -- use .json or .csv")

    if not items:
        raise ValueError(f"{path} loaded but contained no rows")

    normalized = []
    for i, item in enumerate(items):
        normalized.append({
            "id": item.get("id") or f"row-{i}",
            "category": item.get("category") or item.get("attack_type") or "custom",
            "seed": (item.get("seed") or item.get("prompt") or item.get("text") or "").strip(),
        })

    empty = [n["id"] for n in normalized if not n["seed"]]
    if empty:
        raise ValueError(f"these rows have no seed/prompt/text content: {empty}")

    return normalized
