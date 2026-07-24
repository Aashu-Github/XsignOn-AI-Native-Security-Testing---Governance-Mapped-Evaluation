"""garak adapter — parses garak JSONL reports into findings.db."""
import json
import glob
import os
import re
from db import get_connection, insert_finding, make_run_id

GARAK_REPORT_DIR = os.path.expanduser("~/.local/share/garak/garak_runs")


def _run_key(path):
    """Use the garak run UUID in the filename as the stable artifact key."""
    m = re.search(r"garak\.([0-9a-f-]{36})", os.path.basename(path))
    return m.group(1) if m else os.path.basename(path)


def ingest_report(report_path, target_model="llama3.2:3b"):
    run_id = make_run_id("garak", _run_key(report_path))
    print(f"[garak] {os.path.basename(report_path)}  run_id={run_id}")

    conn = get_connection()
    inserted = dupes = skipped = 0

    with open(report_path) as f:
        for line in f:
            if not line.strip():
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                skipped += 1
                continue

            if record.get("entry_type") != "attempt" or record.get("status") != 2:
                continue
            detectors = record.get("detector_results") or {}
            if not detectors:
                continue

            try:
                attack = record["probe_classname"]
                prompt = record["prompt"]["turns"][0]["content"]["text"]
                outputs = record.get("outputs", [])
            except (KeyError, IndexError, TypeError):
                skipped += 1
                continue

            for detector_name, scores in detectors.items():
                for i, output in enumerate(outputs):
                    if not output or i >= len(scores):
                        continue
                    text = output.get("text")
                    if not text:
                        continue
                    score = scores[i]
                    _, ok = insert_finding(
                        source_tool="garak",
                        attack=attack,
                        target_model=target_model,
                        prompt=prompt,
                        response=text,
                        tool_flagged=1 if score is not None and score >= 0.5 else 0,
                        tool_verdict_raw=str(score),
                        tool_rationale=f"{detector_name}: score {score}",
                        run_id=run_id,
                        discriminator=f"{detector_name}:{i}",
                        conn=conn)
                    inserted += ok
                    dupes += (not ok)

    conn.commit()
    conn.close()
    msg = f"[garak] inserted {inserted}"
    if dupes:
        msg += f", skipped {dupes} duplicates"
    if skipped:
        msg += f", {skipped} malformed"
    print(msg)
    return inserted


def ingest(report_path=None, target_model="llama3.2:3b",
           report_dir=GARAK_REPORT_DIR, all_reports=False):
    reports = sorted(glob.glob(os.path.join(report_dir, "*.report.jsonl")),
                     key=os.path.getmtime)
    if not reports:
        print("[garak] no reports found")
        return 0
    if report_path:
        targets = [report_path]
    elif all_reports:
        targets = reports
    else:
        targets = [reports[-1]]
    return sum(ingest_report(p, target_model) for p in targets)


if __name__ == "__main__":
    ingest()