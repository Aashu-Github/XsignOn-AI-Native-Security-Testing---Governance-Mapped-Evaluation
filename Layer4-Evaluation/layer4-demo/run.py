#!/usr/bin/env python3
"""
CLI entrypoint. This is the ENTRYPOINT a k8s Job (pre-deploy gate) or
CronJob (scheduled drift) would run inside the container.

Usage:
    python run.py --target support-chatbot-v3
    python run.py --target kb-assistant-rag-v1
    python run.py --all
    python run.py --target support-chatbot-v3 --live
    python run.py --target support-chatbot-v3 --input-file my_seeds.json

--live and --input-file both require Ollama actually running -- if it
isn't, this exits with a clear error instead of silently using fake scores.
"""

import argparse
import sys
import yaml
import json
from pathlib import Path

from layer4.orchestrator import run_layer4
from layer4.gate import evaluate_gate, print_gate_summary
from layer4.report import write_json, write_html
from layer4.llm_client import OllamaUnavailable

ROOT = Path(__file__).parent


def load_targets() -> list[dict]:
    with open(ROOT / "targets.yaml") as f:
        return yaml.safe_load(f)["targets"]


def load_sample_transcripts() -> list[dict]:
    with open(ROOT / "transcripts" / "sample_transcripts.json") as f:
        return json.load(f)


def ollama_error(host: str, model: str, detail: str = "") -> str:
    return (
        f"\nERROR: Ollama isn't reachable at {host} (model: {model}).\n"
        f"Live mode requires it -- start it and try again:\n\n"
        f"  brew services start ollama    # or: ollama serve\n"
        f"  ollama pull {model}\n"
    )


def ollama_failed_mid_run(detail: str) -> str:
    return f"\nERROR: a live Ollama call failed partway through the run.\n\n{detail}\n"


def run_one(target_cfg: dict, transcripts: list[dict], client=None) -> int:
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
                              "and as the attacked target. REQUIRES Ollama running -- "
                              "errors out if it isn't, rather than falling back. "
                              "Implied automatically by --input-file.")
    parser.add_argument("--input-file",
                         help="path to YOUR OWN .json or .csv file of seed prompts "
                              "(columns/keys: id, category, seed). Implies --live.")
    parser.add_argument("--prompts-per-seed", type=int, default=1,
                         help="how many new prompts to generate per seed row (default 1)")
    parser.add_argument("--model", default="llama3.2:3b",
                         help="Ollama model tag for target + judge (default: llama3.2:3b)")
    parser.add_argument("--ollama-host", default="http://localhost:11434")
    args = parser.parse_args()

    targets = load_targets()
    want_live = args.live or bool(args.input_file)

    client = None
    if want_live:
        from layer4.llm_client import OllamaClient
        client = OllamaClient(model=args.model, host=args.ollama_host)
        if not client.is_available():
            print(ollama_error(args.ollama_host, args.model))
            sys.exit(1)

    try:
        if args.input_file:
            from layer4.data_loader import load_input_file
            from layer4.prompt_generator import generate_prompts
            from layer4.live_attack import get_live_transcripts

            seeds = load_input_file(args.input_file)
            print(f"  loaded {len(seeds)} seed row(s) from {args.input_file}")

            transcripts = generate_prompts(seeds, client, args.prompts_per_seed)
            print(f"  generated {len(transcripts)} new test prompt(s) live with {args.model}")

            transcripts = get_live_transcripts(transcripts, client)
            print(f"  attacked {args.model} directly with the generated prompts, using real responses\n")
        else:
            transcripts = load_sample_transcripts()
            if want_live:
                from layer4.live_attack import get_live_transcripts
                transcripts = get_live_transcripts(transcripts, client)
                print(f"  [live] attacked {args.model} directly, using real responses\n")
    except OllamaUnavailable as e:
        print(ollama_failed_mid_run(str(e)))
        sys.exit(1)
    except (ValueError, FileNotFoundError) as e:
        print(f"\nERROR reading input file: {e}\n")
        sys.exit(1)

    try:
        if args.all:
            exit_code = 0
            for t in targets:
                exit_code |= run_one(t, transcripts, client=client)
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

        sys.exit(run_one(match, transcripts, client=client))
    except OllamaUnavailable as e:
        print(ollama_failed_mid_run(str(e)))
        sys.exit(1)


if __name__ == "__main__":
    main()
