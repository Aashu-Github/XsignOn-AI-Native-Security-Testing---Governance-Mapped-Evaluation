"""Promptfoo adapter — parses a promptfoo JSON export into findings.db."""
import json
import os
from db import get_connection, insert_finding, make_run_id

DEFAULT_EXPORT = "promptfoo_export.json"


def ingest(export_path=DEFAULT_EXPORT):
    """Ingest a promptfoo export. Returns number of findings inserted."""
    if not os.path.exists(export_path):
        print(f"[promptfoo] export not found at {export_path}")
        return 0

    with open(export_path) as f:
        data = json.load(f)

    records = data.get("results", {}).get("results", [])
    conn = get_connection()
    count = 0
    skipped = 0

    for record in records:
        try:
            prompt = record["prompt"]["raw"]
            response = record["response"]["output"]
        except (KeyError, TypeError):
            skipped += 1
            continue

        target_model = record.get("provider", {}).get("id", "unknown")
        grading = record.get("gradingResult") or {}
        success = record.get("success", True)
        score = record.get("score")
        rationale = grading.get("reason", "")

        asserts = (record.get("testCase") or {}).get("assert") or []
        attack = asserts[0].get("type") if asserts else "no-assertion"

        insert_finding(
            source_tool="promptfoo",
            attack=attack,
            target_model=target_model,
            prompt=prompt,
            response=response,
            tool_flagged=0 if success else 1,
            tool_verdict_raw=str(score),
            tool_rationale=rationale,
            conn=conn,
        )
        count += 1

    conn.commit()
    conn.close()
    if skipped:
        print(f"[promptfoo] skipped {skipped} malformed records")
    print(f"[promptfoo] inserted {count} findings")
    return count


if __name__ == "__main__":
    ingest()
    run_id = make_run_id("promptfoo", data.get("evalId", export_path))