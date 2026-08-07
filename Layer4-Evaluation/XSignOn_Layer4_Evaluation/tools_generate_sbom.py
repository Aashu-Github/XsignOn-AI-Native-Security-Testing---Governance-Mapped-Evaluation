from __future__ import annotations

import hashlib
import importlib.metadata
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


packages = sorted(
    ({"name": dist.metadata.get("Name", dist.name), "version": dist.version} for dist in importlib.metadata.distributions()),
    key=lambda item: item["name"].lower(),
)
tracked = []
for relative in [
    "requirements-core.txt",
    "requirements-full.txt",
    "data/healthcare-dataset-stroke-data.csv",
    "config/default_config.json",
]:
    path = ROOT / relative
    if path.exists():
        tracked.append({"path": relative, "sha256": sha256(path), "bytes": path.stat().st_size})

payload = {
    "format": "xsignon-local-software-inventory-v1",
    "generated_at": datetime.now(timezone.utc).isoformat(),
    "packages": packages,
    "tracked_artifacts": tracked,
    "limitations": [
        "This is an inventory and integrity snapshot, not a vulnerability scan.",
        "Model, dataset, and third-party service provenance must be reviewed separately.",
    ],
}
output = ROOT / "evidence" / "sbom.json"
output.write_text(json.dumps(payload, indent=2), encoding="utf-8")
print(f"Wrote {output}")
