from __future__ import annotations

import argparse
import json

from layer4.config import load_config
from layer4.orchestrator import EvaluationOrchestrator


def main() -> None:
    parser = argparse.ArgumentParser(description="Run XSignOn Layer 4 evaluation from the command line")
    parser.add_argument("--config", default=None, help="Optional JSON configuration file")
    parser.add_argument("--target", choices=["local-record", "gemini", "ollama", "trace-file"], default=None)
    parser.add_argument("--model", default=None)
    parser.add_argument("--records", type=int, default=None)
    parser.add_argument("--repeat", type=int, default=None)
    parser.add_argument("--deepeval", action="store_true")
    parser.add_argument("--ragas", action="store_true")
    parser.add_argument("--judge-provider", choices=["gemini", "ollama", "openai-default"], default=None)
    parser.add_argument("--judge-model", default=None)
    parser.add_argument("--set-baseline", action="store_true", help="Set this completed run as the regression baseline")
    args = parser.parse_args()

    overrides: dict = {}
    if args.target or args.model:
        overrides["target"] = {}
        if args.target:
            overrides["target"]["provider"] = args.target
        if args.model:
            overrides["target"]["model"] = args.model
    if args.records or args.repeat:
        overrides["run"] = {}
        if args.records:
            overrides["run"]["max_records"] = args.records
        if args.repeat:
            overrides["run"]["repeat_count"] = args.repeat
    if args.deepeval or args.ragas or args.judge_provider or args.judge_model:
        overrides["judge"] = {
            "enable_deepeval": args.deepeval,
            "enable_ragas": args.ragas,
        }
        if args.judge_provider:
            overrides["judge"]["provider"] = args.judge_provider
        if args.judge_model:
            overrides["judge"]["model"] = args.judge_model

    config = load_config(args.config, overrides)

    def progress(update):
        print(f"[{update.get('progress', 0):3}%] {update.get('message', '')}")

    orchestrator = EvaluationOrchestrator(config)
    report = orchestrator.run(progress=progress)
    if args.set_baseline:
        orchestrator.storage.set_baseline(report["run_id"])
        print(f"Baseline set to {report['run_id']}")
    print(json.dumps({
        "run_id": report["run_id"],
        "verdict": report["gate"]["verdict"],
        "report_html": report["artifacts"]["report_html"],
        "report_json": report["artifacts"]["report_json"],
    }, indent=2))
    raise SystemExit(0 if report["gate"]["verdict"] == "PASS" else 1)


if __name__ == "__main__":
    main()
