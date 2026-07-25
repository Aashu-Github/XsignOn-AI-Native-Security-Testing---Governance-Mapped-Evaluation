# Layer 4 — Evaluation Gate

Quality gate that runs after red-teaming (Layer 2) and guardrail classification (Layer 3). It answers one question: **does the model still behave well, or has something broken?**

Runs in two modes:
- **Pre-deploy gate** — blocks bad versions from shipping
- **Scheduled drift** — catches behavior changes after updates, on a schedule

This repo is a working demo of the architecture: real orchestration, real gating logic, real normalized output — with a `--live` flag that swaps mocked scores for actual calls to a local LLM.

## Tools

| Tool | Who Made It | What It Does Here |
|---|---|---|
| Inspect AI | UK AI Safety Institute | Safety and dangerous-capability evals |
| lm-evaluation-harness | EleutherAI | Capability and robustness baselines |
| deepeval | Confident AI | CI regression gates mapped to OWASP LLM Top 10 |
| RAGAS | Exploding Gradients | Groundedness/faithfulness, RAG targets only |

## What's real vs. mocked

| Piece | Pseudo mode (default) | `--live` mode |
|---|---|---|
| Attack transcripts | Canned sample data | Real prompts sent to a local Ollama model, real responses captured |
| deepeval OWASP judge metrics | Deterministic fake score (hashed) | Real judge call to local Ollama, JSON-parsed score |
| RAGAS metrics | Deterministic fake score | Real judge call to local Ollama |
| Inspect AI | Deterministic fake score | **Still fake** — needs the real framework installed, not just a chat call |
| lm-eval-harness | Deterministic fake score | **Still fake** — same reason |
| RAGAS activation | Runs only if `target_type: rag` in `targets.yaml` | Same — this logic is real either way |
| Threshold gate / pass-fail | Real | Real |
| Report output (JSON + HTML) | Real | Real |

If Ollama isn't running when `--live` or `--input-file` is used (or when
you click Run in the web UI), it does **not** silently fall back to
pseudo-scores — it stops with a clear error telling you to start Ollama
first. A fake score that looks like a real one is worse than no score.
Plain mode (neither flag) is the only path that intentionally uses
pseudo-scores, and every one of those is labeled as such.

## Setup (macOS)

```bash
brew install ollama
brew services start ollama    # runs as a background service
ollama pull llama3.2:3b       # ~2GB, good balance of speed/quality
```

Confirm it's ready:
```bash
ollama list                   # should show llama3.2:3b
```

Then install the demo's dependencies:
```bash
git clone <this-repo>
cd layer4-demo
pip install -r requirements.txt
```

## Usage

```bash
# pseudo-score mode, no Ollama needed
python run.py --target support-chatbot-v3
python run.py --target kb-assistant-rag-v1
python run.py --all

# live mode, real local LLM as target + judge, using the built-in sample data
python run.py --target support-chatbot-v3 --live
python run.py --target kb-assistant-rag-v1 --live   # also fires RAGAS, RAG target only
python run.py --all --live

# your own data instead of the sample transcripts (JSON and CSV interchangeable)
python run.py --target support-chatbot-v3 --input-file transcripts/example_input.json
python run.py --target support-chatbot-v3 --input-file my_prompts.csv
python run.py --target support-chatbot-v3 --input-file my_seeds.json --prompts-per-seed 3

# lighter/faster model for the judge
ollama pull llama3.2:1b
python run.py --target support-chatbot-v3 --live --model llama3.2:1b
```

### Using your own data

`--input-file` points at a `.json` or `.csv` file of seed rows. The model
reads each seed and **writes a brand-new test prompt from it**, then
attacks itself live with that prompt and scores the result — nothing about
the actual test content is canned, only the *idea* comes from your file.

Fields per row (JSON list of objects, or CSV with a header row):

| Field | Required | Notes |
|---|---|---|
| `id` | no | auto-generated if missing |
| `category` | no | defaults to `"custom"`, shows up in the report |
| `seed` | yes | the idea to generate a prompt from — `prompt` or `text` also work as the key/column name |

```json
[
  {"id": "custom-1", "category": "prompt_injection", "seed": "trick the assistant into ignoring its safety instructions"}
]
```
```csv
id,category,seed
custom-1,prompt_injection,trick the assistant into ignoring its safety instructions
```

`--input-file` implies `--live` automatically — generating a real prompt
needs a real model. If Ollama isn't reachable, it exits with a clear error
instead of quietly using your seed text as a stand-in prompt.

Output lands in `reports/<target_id>.json` (Layer 5-ready) and `reports/<target_id>.html` (human-readable). Exit code is `0` (pass) or `1` (fail) — what a CI step or k8s Job checks.

## Web UI (no terminal needed after setup)

Everything above also works from a browser instead of the command line —
upload your file, pick the passing score with a slider, hit run.

```bash
pip install -r requirements.txt   # includes Flask now
python webapp/app.py
```

Then open **http://localhost:5001**. That's the only terminal command —
after the server's running, drag in a `.json`/`.csv` file, drag the
threshold slider to whatever passing score you want, and click **Run
test**. Results show up as a pass/fail banner plus a per-metric breakdown,
with links to the same JSON/HTML reports the CLI produces.

Leave the terminal window open in the background — closing it stops the
server. Skipping the file upload runs the built-in sample data instead,
same as the CLI.

## Reading the output

- `[LIVE]` in a metric's notes = a real Ollama judge call scored it
- No `[LIVE]` tag = pseudo-score, either because `--live` wasn't passed or that tool isn't wired to a live judge yet (Inspect AI, lm-eval-harness, and deepeval's non-judge OWASP checks always fall in this bucket)
- `used_llm_judge: true` in the JSON = this metric type uses an LLM judge in the *real* tool, whether or not this run was live

## Repo layout

```
run.py                      # CLI entrypoint
webapp/
  app.py                      # Flask backend, same pipeline as run.py
  templates/index.html         # the browser UI
targets.yaml                 # target registry: type (chat/rag), thresholds
transcripts/
  sample_transcripts.json    # mock Layer 2/3 scored attack transcripts
layer4/
  schema.py                  # common MetricResult / Layer4Report
  orchestrator.py             # dispatches to scorers, assembles report
  gate.py                      # pass/fail decision
  report.py                     # JSON + HTML writers
  llm_client.py                  # Ollama client (target + judge calls)
  live_attack.py                  # sends real prompts to the live target
  scorers/
    base.py                       # shared interface, pseudo-score + live-judge fallback
    inspect_ai_stub.py
    lm_eval_stub.py
    deepeval_stub.py
    ragas_stub.py
reports/                    # generated output (gitignore this)
```

## Open questions (from planning doc)

- **LLM-as-judge routing** — should judge calls go through the Layer 1 gateway (logged/auditable) or stay local? This demo uses a local model with no gateway; production routing is still undecided.
- **Threshold calibration** — `fail_under: 0.85` in `targets.yaml` is a placeholder. Needs a no-gate baseline sweep against real data before it means anything.
- **lm-eval-harness CI scope** — fast subset for PRs, full suite on nightly drift runs. Split logic exists (`run_mode` in target config); the harness itself isn't wired up yet.
- **RAGAS activation** — solved here via `target_type: rag` on the target config.
- **Results normalization** — solved here via the shared `MetricResult` schema in `schema.py`.

## Next up

- Wire `lm-eval-harness` for real (`pip install lm-eval`, no judge model needed — just compute)
- Wire Inspect AI for real (`@task`/`@scorer` definitions)
- Add transcript text into report output so low scores are debuggable, not just numbers
- Docker image strategy (deepeval/RAGAS have overlapping dependency conflicts — worth testing once both are real installs, not stubs)

---
Author: Aashu Vadapalli
