# Layer 3 POC Features

## Completed Features

### 1. Local GPU Guardrail Runtime

- Runs locally on a Windows GPU machine
- Uses Ollama for local model serving
- Uses `granite4.1-guardian:8b` as the guardrail model
- Uses `llama3.2` as the main local LLM
- Does not depend on a cloud API for inference

### 2. Input Guardrail

Before the main LLM sees the prompt, Layer 3 checks the input for selected risk categories.

Current categories:

```text
jailbreak
profanity
violence
harm
```

Possible decision:

```text
BLOCKED_BEFORE_MODEL
```

This means the prompt was risky and never reached the main LLM.

### 3. Main LLM Generation

If the input passes the guardrail, the prompt is sent to:

```text
llama3.2
```

The main model generates the response.

### 4. Output Guardrail

After the main model responds, Layer 3 can check the generated output before showing it to the user.

Possible decision:

```text
BLOCKED_AFTER_MODEL
```

This means the user prompt was allowed, but the model output was risky.

### 5. Final Decision System

The pipeline returns one of three decisions:

```text
ALLOWED
BLOCKED_BEFORE_MODEL
BLOCKED_AFTER_MODEL
```

### 6. Browser Dashboard

The dashboard provides:

- Prompt input
- Safe example button
- Unsafe example button
- Fast Demo Mode
- Strict Guardrail Mode
- Audit Mode
- Risk category checkboxes
- Temperature control
- Context-size control
- Output guardrail toggle
- Final decision card
- Severity display
- Risk score
- Blocked risk tags
- Final response viewer
- Raw JSON viewer
- Recent audit logs
- Runtime metrics
- Benchmark evaluation

### 7. Runtime Metrics

The dashboard tracks:

- Total logged runs
- Allowed runs
- Blocked-before-model runs
- Blocked-after-model runs
- Average latency
- Risk category counts

### 8. Benchmark Evaluation

The benchmark panel reports:

```text
accuracy
precision
recall
F1 score
false positive rate
false negative rate
true positives
true negatives
```

This makes the project more useful than a basic prompt demo because it supports measurable evaluation.

### 9. Audit Logs

The backend writes structured JSONL logs.

Each run can include:

- timestamp
- original prompt
- input guardrail results
- main model response
- output guardrail results
- blocked risks
- final decision
- latency

### 10. API Endpoints

The FastAPI backend provides:

```text
GET  /
GET  /health
GET  /config
POST /pipeline/run
GET  /logs/recent
GET  /metrics/summary
POST /benchmark/run
```

### 11. POC Run Scripts

The project includes scripts for easier demos:

```text
run_backend.ps1
run_ui.ps1
run_all.ps1
```

The main script:

```powershell
.\run_all.ps1
```

starts the backend, starts the UI, opens the dashboard, and opens the API docs.

## Why This Is Useful

This prototype demonstrates a practical AI guardrail layer that can:

- block unsafe input before the main model sees it
- check generated output before returning it
- produce structured logs for auditing
- expose metrics for evaluation
- support a browser dashboard
- export JSON events for integration with future layers

## Current Limitations

- Benchmark dataset is still small
- Only four risk categories are currently active
- No persistent database yet
- No authentication yet
- No Docker Compose setup yet
- No model comparison panel yet
- No RAG groundedness checks yet
- No multi-user deployment yet
- No hosted version yet

## Future Improvements

1. Add more risk categories.
2. Add model comparison mode.
3. Add RAG groundedness checking.
4. Add answer relevance checking.
5. Add tool-call hallucination checking.
6. Add persistent SQLite or Postgres logging.
7. Add CSV and JSON export.
8. Add authentication.
9. Add Docker Compose.
10. Add screenshots/GIFs to GitHub.
11. Add larger benchmark datasets.
12. Add latency optimization.
13. Add Fast Mode routing optimization.
14. Add Layer 4 evaluation API integration.
15. Add integration with the other team layers.