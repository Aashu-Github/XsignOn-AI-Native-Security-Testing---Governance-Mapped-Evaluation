"""
Local web frontend for the Layer 4 demo. Wraps the exact same pipeline
run.py uses (layer4/orchestrator.py etc.) -- this isn't a separate
implementation, it's a browser on top of the same code.

Start it with:
    python webapp/app.py
Then open http://localhost:5001 in a browser. One terminal command to
start the server; everything after that is point-and-click.
"""

import sys
import json
import copy
import tempfile
from pathlib import Path

import yaml
from flask import Flask, request, jsonify, render_template, send_file

ROOT = Path(__file__).resolve().parent.parent  # layer4-demo/
sys.path.insert(0, str(ROOT))

from layer4.orchestrator import run_layer4
from layer4.gate import evaluate_gate
from layer4.report import write_json, write_html
from layer4.data_loader import load_input_file
from layer4.prompt_generator import generate_prompts
from layer4.live_attack import get_live_transcripts
from layer4.llm_client import OllamaClient, OllamaUnavailable

app = Flask(__name__)


def load_targets() -> list[dict]:
    with open(ROOT / "targets.yaml") as f:
        return yaml.safe_load(f)["targets"]


def load_sample_transcripts() -> list[dict]:
    with open(ROOT / "transcripts" / "sample_transcripts.json") as f:
        return json.load(f)


def apply_uniform_threshold(target_cfg: dict, threshold: float) -> dict:
    """Overrides every configured threshold with the one number the user
    picked in the UI -- that's what 'choose the passing score' controls."""
    cfg = copy.deepcopy(target_cfg)
    for _tool, metrics in cfg.get("thresholds", {}).items():
        for k in metrics:
            metrics[k] = threshold
    return cfg


@app.route("/")
def index():
    return render_template("index.html", targets=load_targets())


@app.route("/api/run", methods=["POST"])
def api_run():
    target_id = request.form.get("target_id")
    try:
        threshold = float(request.form.get("threshold", 0.85))
    except ValueError:
        return jsonify({"error": "threshold must be a number between 0 and 1"}), 400
    threshold = max(0.0, min(1.0, threshold))
    model = request.form.get("model") or "llama3.2:3b"
    try:
        prompts_per_seed = max(1, int(request.form.get("prompts_per_seed", 1)))
    except ValueError:
        prompts_per_seed = 1

    targets = load_targets()
    target_cfg = next((t for t in targets if t["target_id"] == target_id), None)
    if not target_cfg:
        return jsonify({"error": f"unknown target '{target_id}'"}), 400
    target_cfg = apply_uniform_threshold(target_cfg, threshold)

    client = OllamaClient(model=model)
    if not client.is_available():
        return jsonify({
            "error": f"Ollama isn't reachable at {client.host} (model: {model}). "
                     f"This app runs in live mode only -- start Ollama and try again: "
                     f"`brew services start ollama` (or `ollama serve`), then "
                     f"`ollama pull {model}`."
        }), 503

    notes = []
    uploaded = request.files.get("file")
    try:
        if uploaded and uploaded.filename:
            suffix = Path(uploaded.filename).suffix.lower()
            if suffix not in (".json", ".csv"):
                return jsonify({"error": "only .json or .csv files are supported"}), 400
            with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
                uploaded.save(tmp.name)
                try:
                    seeds = load_input_file(tmp.name)
                except (ValueError, FileNotFoundError) as e:
                    return jsonify({"error": str(e)}), 400

            transcripts = generate_prompts(seeds, client, prompts_per_seed)
            notes.append(f"generated {len(transcripts)} test prompt(s) live from "
                         f"{len(seeds)} seed row(s) in {uploaded.filename}")
        else:
            transcripts = load_sample_transcripts()
            notes.append("no file uploaded -- used the built-in sample transcripts")

        transcripts = get_live_transcripts(transcripts, client)
        notes.append(f"attacked {model} live and used its real responses")

        report = run_layer4(target_cfg, transcripts, client=client)
    except OllamaUnavailable as e:
        return jsonify({
            "error": f"A live Ollama call failed partway through the run: {e}"
        }), 503

    out_dir = ROOT / "reports"
    out_dir.mkdir(exist_ok=True)
    write_json(report, str(out_dir / f"{report.target_id}.json"))
    write_html(report, str(out_dir / f"{report.target_id}.html"))

    result = report.to_dict()
    result["notes"] = notes
    result["threshold_used"] = threshold
    result["report_html_url"] = f"/reports/{report.target_id}.html"
    result["report_json_url"] = f"/reports/{report.target_id}.json"
    return jsonify(result)


@app.route("/reports/<path:filename>")
def serve_report(filename):
    return send_file(ROOT / "reports" / filename)


if __name__ == "__main__":
    print("\n  Layer 4 web UI running -- open http://localhost:5001 in your browser\n")
    app.run(debug=True, port=5001)
