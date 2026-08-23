# XSignOn Layer 4 — Evaluation

Layer 4 evaluates how an AI target behaves and decides whether the run should pass or fail. It is designed to work locally today and later accept traces from Layers 2 and 3 without changing the evaluators.

The web console follows the same dark operations-console layout across the main dashboard, metric selection, run history, results, evidence, and generated HTML reports.

## What Layer 4 checks

Layer 4 currently covers:

- **Correctness** — field accuracy, required facts, numeric tolerance, and JSON validity.
- **Groundedness** — whether answers are supported by retrieved context.
- **Safety** — information leakage, unsafe medical behavior, dangerous output, and unauthorized tool calls.
- **Robustness** — prompt injection, indirect injection, hidden-context extraction, and poisoned context.
- **Consistency** — paraphrase agreement and repeated-run agreement.
- **Regression** — compares the current run with a selected baseline.
- **Judge calibration** — compares semantic judge scores with optional human ratings.
- **OWASP evidence** — maps evaluation evidence to the OWASP GenAI / LLM Top 10 2026 taxonomy.

Layer 4 does **not** generate random or canned scores. If an enabled evaluator fails, the run records the error instead of inventing a result.

## Main flow

```text
Target output
    ↓
Core deterministic checks
    ↓
Optional DeepEval / RAGAS judges
    ↓
Metric thresholds + critical safety checks
    ↓
PASS / FAIL gate
    ↓
Evidence + report + regression history
```

## Quick start on macOS

From the repository root:

```bash
cd Layer4-Evaluation/XSignOn_Layer4_Evaluation
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
```

For core mode only:

```bash
python run_web.py
```

For DeepEval, RAGAS, or Gemini support:

```bash
python -m pip install -r requirements-full.txt
python run_web.py
```

Open:

```text
http://127.0.0.1:8080
```

## Using Ollama

Install and start Ollama, then pull the model you want to test. For example:

```bash
ollama pull llama3.2
ollama serve
```

The **target model** is the model being tested.

The **judge model** is the model evaluating the target. They do not need to be the same model.

A practical local setup is:

```text
Target model: llama3.2:latest
Judge model:  qwen3:14b
```

For Macs with less available memory, use `qwen3:8b` as the judge.

Install the recommended local judge with:

```bash
ollama pull qwen3:14b
```

## DeepEval and RAGAS

Enable them from the **Semantic evaluation** section in the console.

DeepEval currently provides semantic checks for:

- correctness
- faithfulness
- answer relevancy

RAGAS currently provides:

- faithfulness
- context precision
- context recall

RAGAS only runs on answer cases that have retrieved context.

### RAGAS on macOS

Install the full dependencies:

```bash
source .venv/bin/activate
python -m pip install -r requirements-full.txt
```

This project pins the supported RAGAS version and includes the LangChain compatibility needed by the current RAGAS import path.

If RAGAS reports a missing-package error, first verify that you are using the same virtual environment that runs `run_web.py`:

```bash
which python
python -m pip show ragas
python -m pip show langchain-google-vertexai
```

Then restart the server.

For local RAGAS judging:

```text
RAGAS:          enabled
Judge provider: Ollama
Judge model:    qwen3:14b
```

A smaller model may run, but a stronger judge generally gives more reliable evaluation behavior. There is no fixed RAGAS model-size requirement.

## Using Gemini

Install the full requirements and set the key in the same terminal that starts Layer 4:

```bash
export GEMINI_API_KEY="your-key"
python run_web.py
```

Then choose **Gemini API** for the target or judge in the console.

API keys are read from environment variables. They are not entered in the web page and are not written to reports.

## Choosing metrics

Click **Choose metrics** from the main console.

- Metrics under **Tested** run and can affect PASS / FAIL.
- Metrics under **Not tested** are skipped.
- Technical integrity checks stay active so a broken target or missing enabled evaluator cannot look like a passing run.
- Metric selection is saved in the browser.

Turning off a metric reduces evaluation coverage; it does not mean the associated risk is safe.

## Gate behavior

The default gate fails when:

- an enabled metric is below its threshold,
- a critical security check fails,
- an enabled evaluator cannot run, or
- regression exceeds the configured allowed drop.

Critical checks include private-data leakage, hidden-context leakage, cross-patient disclosure, unsafe medical behavior, dangerous output, unauthorized tool calls, and invalid JSON when JSON is required.

Thresholds and gate behavior are configured in:

```text
config/default_config.json
```

## Run history and baseline

Every completed run appears in **Run History**.

A reviewed, known-good run can be set as the regression baseline. Later runs compare common aggregate metrics with that baseline.

Do not automatically promote every passing run to baseline; use a run that has been reviewed and accepted.

## Reports and evidence

Every run creates:

```text
reports/runs/<run-id>/
├── config.json
├── cases.jsonl
├── traces.jsonl
├── metrics.jsonl
├── report.json
└── report.html
```

The HTML report uses the same Layer 4 console visual language as the web application.

The run manifest records items such as the target model, judge model, dataset hash, test-suite hash, environment, and baseline. API keys are not written to the report.

## Medical dataset

The bundled stroke dataset is used for structured extraction, summarization, retrieval, privacy, grounding, injection, hidden-context, consistency, and input-limit tests.

It is **not** used to validate clinical diagnosis, treatment, or future stroke prediction. The project is an AI evaluation framework, not a medical device.

Do not send identifiable patient data to an external judge unless the required privacy, security, legal, and provider controls are in place.

## Connecting Layers 2 and 3

Layer 4 can evaluate upstream traces instead of calling a model directly.

See:

```text
docs/UPSTREAM_TRACE_SCHEMA.md
```

The intended flow is:

```text
Layer 2 / Layer 3 traces
        ↓
trace-file target
        ↓
Layer 4 evaluators
        ↓
gate + evidence + reporting
```

## CLI examples

Run the default evaluation:

```bash
python run_cli.py
```

Run more records with repeated attempts:

```bash
python run_cli.py --records 12 --repeat 3
```

Run with Gemini and semantic judges:

```bash
python run_cli.py \
  --target gemini \
  --model gemini-3.6-flash \
  --deepeval \
  --ragas \
  --judge-provider gemini \
  --judge-model gemini-3.6-flash
```

A passing CLI run exits with code `0`; a failed gate exits with code `1`, so it can be used in CI/CD.

## Tests

```bash
python -m unittest discover -s tests -v
```

Core tests run offline. External DeepEval, RAGAS, Gemini, and Ollama calls require their packages and services.

## Troubleshooting

### Ollama is not reachable

```bash
ollama serve
ollama list
```

Confirm the exact configured model name appears in `ollama list`.

### Port 8080 is already in use

```bash
python run_web.py --port 8090
```

### DeepEval or RAGAS fails

Check:

1. the virtual environment is activated,
2. `requirements-full.txt` is installed,
3. the selected judge model exists or the API key is set,
4. Ollama or the external provider is reachable, and
5. the error field in `metrics.jsonl` for the exact failure.

Layer 4 intentionally records evaluator failures instead of falling back to fake scores.

## Project layout

```text
XSignOn_Layer4_Evaluation/
├── run_web.py
├── run_cli.py
├── config/
├── data/
├── layer4/
│   ├── datasets/
│   ├── evaluators/
│   ├── judges/
│   ├── reporting/
│   ├── targets/
│   └── orchestrator.py
├── web/
├── evidence/
├── reports/
├── scripts/
├── tests/
└── docs/
```

## License

MIT licensed. Layer 4 provides evaluation evidence and gating support; it does not by itself prove regulatory compliance, system safety, or clinical suitability.
