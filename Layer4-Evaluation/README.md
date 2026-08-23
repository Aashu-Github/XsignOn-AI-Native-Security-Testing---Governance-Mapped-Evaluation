# Layer 4 — Evaluation

Layer 4 is XSignOn's evaluation and release-gating layer. It measures how an AI target behaves, records evidence, and decides whether the configured checks pass or fail.

The working implementation is here:

```text
Layer4-Evaluation/XSignOn_Layer4_Evaluation/
```

See the [implementation README](XSignOn_Layer4_Evaluation/README.md) for setup, macOS instructions, DeepEval/RAGAS configuration, Ollama judge models, metric selection, reports, and troubleshooting.

## Where Layer 4 fits

```text
Layer 1 — target access
        ↓
Layer 2 — offensive testing
        ↓
Layer 3 — classification / guardrails
        ↓
Layer 4 — evaluation + gate
        ↓
Layer 5 — governance crosswalk
        ↓
Layer 6 — reporting / evidence
```

Layer 4 can call a target directly or evaluate traces supplied by upstream layers.

## What it evaluates

The current implementation includes:

- correctness and required-fact coverage,
- groundedness and faithfulness,
- safety and policy checks,
- prompt-injection and robustness tests,
- consistency checks,
- optional DeepEval and RAGAS semantic evaluation,
- regression against a reviewed baseline,
- judge calibration with optional human ratings,
- OWASP GenAI / LLM Top 10 evidence mapping, and
- PASS / FAIL gating.

## Web console

The Layer 4 web experience uses one consistent dark operations-console layout for:

- Evaluation Overview
- New Evaluation
- Metric Selection
- Results
- Evidence
- Run History
- Generated HTML Reports

The UI is a presentation layer over the real evaluation harness; evaluator behavior and evidence generation remain in the Python backend.

## Local judges

The model being tested and the model judging it can be different.

A practical local setup is:

```text
Target: llama3.2:latest
Judge:  qwen3:14b
```

`qwen3:8b` is a lighter local judge option for Macs with less available memory. RAGAS does not have a fixed minimum model size, but stronger judge models are generally more reliable for semantic scoring.

## Important limitation

Layer 4 produces evaluation evidence. It does not by itself prove that an AI system is secure, compliant, clinically safe, or ready for production. Final decisions should combine Layer 4 results with the surrounding technical, governance, and human-review controls.
