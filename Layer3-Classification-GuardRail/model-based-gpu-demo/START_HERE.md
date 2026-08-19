# Layer 3 GPU Guardrail POC — Start Here

## What This Is

This is the Layer 3 Classification & GuardRail proof-of-concept for the AI Native Security Testing project.

It runs a local AI guardrail pipeline using:

```text
Guardrail Model: granite4.1-guardian:8b
Main LLM: llama3.2
Runtime: Ollama
Backend: FastAPI
Frontend: HTML/CSS/JavaScript dashboard
```

## Current Pipeline

```text
User Prompt
→ Input Guardrail
→ Main LLM
→ Output Guardrail
→ Final Decision
→ JSON Audit Log
→ Dashboard Metrics
```

## Main Features

- Local GPU-based guardrail model
- Input safety checks before the main LLM
- Output safety checks after the main LLM
- FastAPI backend
- Browser-based dashboard
- Fast Demo Mode, Strict Guardrail Mode, and Audit Mode
- Risk categories: jailbreak, profanity, violence, harm
- Runtime metrics
- Recent audit logs
- Benchmark evaluation
- Accuracy, precision, recall, and F1 score
- False positive and false negative rates
- JSON event export for future evaluation layers

## How To Run

From this folder:

```powershell
.\run_all.ps1
```

This opens:

```text
Backend API: http://127.0.0.1:8000
API Docs:    http://127.0.0.1:8000/docs
Dashboard:   http://127.0.0.1:5173
```

If PowerShell blocks scripts, run:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

Then run:

```powershell
.\run_all.ps1
```

## Demo Order

1. Open the dashboard.
2. Confirm the API status says Online.
3. Select Fast Demo Mode for a live demo.
4. Click Safe Example.
5. Click Run Pipeline.
6. Show that the final decision is ALLOWED.
7. Click Unsafe Example.
8. Click Run Pipeline.
9. Show that the final decision is BLOCKED_BEFORE_MODEL.
10. Show Runtime Metrics.
11. Show Benchmark Evaluation.
12. Show Recent Audit Logs.
13. Explain that the JSON output can be sent to the next evaluation layer.

## Mode Explanation

### Fast Demo Mode

Fast Mode checks fewer categories and disables output guardrail checks to make live demos faster.

Best for quick presentations.

### Strict Guardrail Mode

Strict Mode checks all current risk categories and runs both input and output guardrails.

Best for showing the full pipeline.

### Audit Mode

Audit Mode is used when saved logs and evidence matter.

Best for evaluation, debugging, and traceability.

## Why This Matters

This prototype shows that a guardrail layer should not only block unsafe prompts. It should also produce structured evidence that can be reviewed, measured, logged, and passed to later layers.

Layer 3 can output JSON containing:

- original prompt
- input guardrail results
- blocked risks
- main model response
- output guardrail results
- final decision
- latency
- benchmark metrics
- audit logs

## Current Limitations

- Benchmark dataset is still small
- Risk categories are limited
- No database yet
- No authentication yet
- No Docker Compose packaging yet
- No RAG groundedness checks yet
- No full multi-layer orchestration yet

## Next Goals

- Add more risk categories
- Add model comparison
- Add RAG groundedness checks
- Add answer relevance checks
- Add persistent database logging
- Add Docker Compose
- Add screenshots and GIFs for GitHub
- Add integration with other project layers