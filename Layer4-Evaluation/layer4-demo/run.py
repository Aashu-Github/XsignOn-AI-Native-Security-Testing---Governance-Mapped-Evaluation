#!/usr/bin/env python3
"""
CLI entrypoint. This is the ENTRYPOINT a k8s Job (pre-deploy gate) or
CronJob (scheduled drift) would run inside the container.

Usage:
    python run.py --target support-chatbot-v3
    python run.py --target kb-assistant-rag-v1
    python run.py --all
"""

import argparse
import sys
import yaml
import json
from pathlib import Path

from layer4.orchestrator import run_layer4
from layer4.gate import evaluate_gate, print_gate_summary
from layer4.report import write_json, write_html

ROOT = Path(__file__).parent


def load_targets() -> list[dict]:
    with open(ROOT / "targets.yaml") as f:
        return yaml.safe_load(f)["targets"]


def load_transcripts() -> list[dict]:
    with open(ROOT / "transcripts" / "sample_transcripts.json") as f:
        return json.load(f)


def run_one(target_cfg: dict, transcripts: list[dict], client=None, live_attack: bool = False) -> int:
    if live_attack and client is not None:
        from layer4.live_attack import get_live_transcripts
        transcripts, was_live = get_live_transcripts(transcripts, client)
        if was_live:
            print(f"  [live] attacked {client.model} directly, using real responses")
        else:
            print(f"  [live attack requested but Ollama unreachable -- used canned transcripts]")

    report = run_layer4(target_cfg, transcripts, client=client)
    print_gate_summary(report)

    out_dir = ROOT / "reports"
    out_dir.mkdir(exist_ok=True)
    json_path = out_dir / f"{report.target_id}.json"
    html_path = out_dir / f"{report.target_id}.html"
    write_json(report, str(json_path))
    write_html(report, str(html_path))
    print(f"  wrote {json_path}")
    print(f"  wrote {html_path}")

    return evaluate_gate(report)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", help="target_id from targets.yaml")
    parser.add_argument("--all", action="store_true", help="run every registered target")
    parser.add_argument("--live", action="store_true",
                         help="use a real local Ollama model as judge (deepeval/RAGAS) "
                              "and as the attacked target, instead of pseudo-scores")
    parser.add_argument("--model", default="llama3.2:3b",
                         help="Ollama model tag to use when --live is set (default: llama3.2:3b)")
    parser.add_argument("--ollama-host", default="http://localhost:11434")
    args = parser.parse_args()

    targets = load_targets()
    transcripts = load_transcripts()

    client = None
    if args.live:
        from layer4.llm_client import OllamaClient
        client = OllamaClient(model=args.model, host=args.ollama_host)
        if not client.is_available():
            print(f"[warning] Ollama not reachable at {args.ollama_host} -- "
                  f"is `ollama serve` running? Falling back to pseudo-scores for this run.\n")

    if args.all:
        exit_code = 0
        for t in targets:
            exit_code |= run_one(t, transcripts, client=client, live_attack=args.live)
        sys.exit(exit_code)

    if not args.target:
        print("pass --target <target_id> or --all. Available targets:")
        for t in targets:
            print(f"  - {t['target_id']} ({t['target_type']}, {t['run_mode']})")
        sys.exit(2)

    match = next((t for t in targets if t["target_id"] == args.target), None)
    if not match:
        print(f"unknown target: {args.target}")
        sys.exit(2)

    sys.exit(run_one(match, transcripts, client=client, live_attack=args.live))


if __name__ == "__main__":
    main()
