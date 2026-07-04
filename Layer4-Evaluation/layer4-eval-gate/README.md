# Layer 4 — Evaluation Gate

Real implementation of the Layer 4 CI gate described in the design doc:
scores a target model against OWASP LLM Top 10 with `deepeval`, and
conditionally activates `RAGAS` faithfulness/relevancy scoring when the
target is a RAG stack. Runs as a CLI, a pytest suite, or a container —
your call.

This replaces the [demo artifact](./layer4_deepeval_ragas_gate.html) you
had, which used hardcoded fake scores to visualize the gate's *behavior*.
This repo does the same thing against a **real** target: it sends probes
through your Layer 1 gateway, scores the actual responses, and produces
the same style of report from real numbers.

## How it works

```
suite.yaml -----> which target, which dataset, which thresholds
targets/*.yaml --> where the real model lives + how to call it (type: chat|rag)
datasets/*.jsonl -> probes, one per OWASP category (extend this freely)

layer4/gateway_client.py -> sends each probe to the target via the Layer 1 gateway
layer4/owasp_metrics.py  -> maps each OWASP category to a deepeval metric (GEval or built-in)
layer4/ragas_gate.py     -> only runs if target.type == "rag"
layer4/schema.py         -> normalizes deepeval + ragas output into one format
layer4/report.py         -> renders results.json into report.html
layer4/runner.py         -> orchestrates all of the above, exit code 0/1 for CI
```

## Answering the open questions from the research doc

- **RAGAS activation**: driven by an explicit `type: rag` field in the
  target's YAML (`targets/internal-kb-assistant.yaml`). No inference —
  whoever onboards a target to Layer 1 declares it.
- **Threshold calibration**: `suite.yaml`'s `fail_under` is still a
  starting guess (0.85), same as the doc flags. `category_overrides` lets
  you loosen thresholds per-category (LLM08/excessive agency ships at
  0.75 here, since its automated scoring is the thinnest per the doc's
  notes) while you collect a baseline sweep to calibrate the rest.
- **LLM-as-judge routing**: `judge_model` is a plain string in
  `suite.yaml`. Point `GatewayClient`/deepeval's `model=` at your in-cluster
  judge if you want those calls logged through Layer 1 instead of calling
  a provider directly — that's a one-line change in `owasp_metrics.py`
  and `ragas_gate.py`.
- **Results normalization**: every score, from either tool, becomes a
  `MetricResult` (`layer4/schema.py`) before anything downstream touches
  it. That's the shape Layer 5 should consume.
- **Image strategy**: one `Dockerfile` here installs both `deepeval` and
  `ragas`. If their dependency pins conflict for you, split this into two
  images and have `runner.py`'s two gate functions run in separate Jobs
  that both write to the same `results/` volume.

## Setup

```bash
pip install -r requirements.txt
export OPENAI_API_KEY=sk-...      # or whichever judge provider you configure
```

Edit `targets/example-target.yaml` (or add a new file under `targets/`) to
point at your real model through the Layer 1 gateway. Add probes to
`datasets/owasp_probes.jsonl` — the 10 included are placeholders, one per
category, meant to be replaced/expanded with real adversarial probes from
Layer 2's red-team transcripts.

## Running it

```bash
# CLI runner — writes results/results.json and results/report.html, exits 1 on failure
python -m layer4.runner --suite suite.yaml

# Or, point at a RAG target explicitly
python -m layer4.runner --suite suite.yaml --target targets/internal-kb-assistant.yaml

# Pytest-native alternative (same config, deepeval's own CLI reporting)
deepeval test run tests/test_owasp_gate.py
```

## Running in CI / Kubernetes

- `.github/workflows/layer4-gate.yml` runs the gate on every PR and
  nightly (the doc's two modes: pre-deploy gate + scheduled drift re-run).
- `Dockerfile` builds a stateless image suitable for a k8s `Job` (PR gate)
  or `CronJob` (nightly drift). No local state — everything needed is the
  mounted config/dataset and the `OPENAI_API_KEY`/gateway token secrets.

## Extending

- New OWASP category or a sharper rubric: edit `OWASP_CRITERIA` in
  `layer4/owasp_metrics.py`.
- New target: add a YAML file under `targets/`, set `type: rag` if it's a
  RAG stack.
- More probes: append lines to `datasets/owasp_probes.jsonl` — this is
  meant to grow from real Layer 2 red-team transcripts, not stay at 10
  toy examples.
