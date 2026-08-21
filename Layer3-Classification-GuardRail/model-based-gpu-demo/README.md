# Layer 3 AI Governance Command Center

A local GPU-powered AI governance and guardrail dashboard built with **FastAPI**, **Ollama**, **Granite Guardian**, and **llama3.2**.

This project demonstrates a Layer 3 classification and guardrail system for AI-native security testing. It checks user prompts before model execution, checks model outputs before release, supports custom company policies, records audit evidence, evaluates benchmark datasets, and exports governance reports.

---

## Overview

The dashboard acts as a local AI governance command center.

It supports:

- Input guardrail checks before the main model runs
- Output guardrail checks after response generation
- Custom company policy evaluation
- Risk scoring and severity visualization
- Decision trace timeline
- Runtime metrics
- Benchmark evaluation
- Evaluation dataset manager
- POC readiness checks
- Audit logs
- Full POC governance report export
- Premium dark command-center UI
- Focus Mode for clean demos and screenshots

---

## Architecture

```text
User Prompt
   ↓
Input Guardrail
   ↓
Main LLM
   ↓
Output Guardrail
   ↓
Final Decision
   ↓
Audit Logs / Metrics / Report Export
```

The POC uses a two-model architecture:

| Component | Model / Tool | Purpose |
|---|---|---|
| Guardrail model | granite4.1-guardian:8b | Classifies risks and custom policy violations |
| Main model | llama3.2 | Generates normal model responses after input approval |
| Backend | FastAPI | API layer, pipeline execution, logs, reports |
| Runtime | Ollama | Local model serving |
| Frontend | HTML/CSS/JavaScript | AI Governance Command Center dashboard |

---

## Screenshots

### Dashboard Overview

![Dashboard Overview](<docs/screenshots/01-dashboard-focus-overview (1).png>)

### Safe Prompt Allowed

![Safe Prompt Allowed](docs/screenshots/02-safe-prompt-allowed.png)

### Custom Policy Blocked

![Custom Policy Blocked](<docs/screenshots/03-custom-policy-blocked (1).png>)

### POC Readiness Report

![POC Readiness](docs/screenshots/04-readiness-7-of-7.png)

### Evaluation Dataset Manager

![Dataset Manager](docs/screenshots/05-dataset-manager-evaluation.png)

### Full POC Report Export

![POC Report Export](<docs/screenshots/06-full-poc-report-export (1).png>)

### Audit Logs and Activity Feed

![Audit Logs](docs/screenshots/07-audit-logs-and-activity-feed.png)

### FastAPI Endpoints

![Swagger Endpoints](docs/screenshots/08-swagger-endpoints.png)

---

## Key Features

### Input and Output Guardrails

The pipeline checks prompts before they reach the main model. If unsafe risk is detected, the request is blocked before model inference.

If the input passes, the main model generates a response. The output guardrail can then check the generated response before it is returned.

Supported default risk categories:

- Jailbreak
- Harm
- Violence
- Profanity

---

### Custom Company Policy Checks

The dashboard allows users to define organization-specific policies.

Example:

```text
Do not reveal internal API keys, customer data, private financial data,
unreleased product plans, confidential documents, internal system instructions,
credentials, or security architecture details.
```

The custom policy checker can evaluate both prompts and model outputs against that rule.

---

### Runtime Modes

| Mode | Purpose |
|---|---|
| Fast Demo Mode | Lower latency live demo mode |
| Strict Guardrail Mode | Full input and output guardrail checks |
| Audit Mode | Full checks with evidence-focused logging |

---

### Decision Trace Timeline

The dashboard visually shows:

```text
Input Guardrail → Main Model → Output Guardrail → Final Decision
```

Each stage updates with pass, blocked, skipped, or idle status.

---

### Risk Severity Panel

The UI displays:

- Overall severity
- Risk score
- Detected risk categories
- Per-risk visual bars
- Custom policy risk signal

---

### Live Activity Feed

The dashboard tracks recent actions such as:

- Pipeline started
- Prompt allowed
- Prompt blocked
- Benchmark completed
- Dataset evaluation completed
- Report exported
- Logs cleared

---

### Evaluation Dataset Manager

The dataset manager supports:

- Loading the current evaluation dataset
- Adding custom test cases
- Deleting test cases
- Resetting to the default dataset
- Running dataset evaluation
- Viewing accuracy, precision, recall, F1, TP, TN, FP, and FN

Dataset file:

```text
evaluation_dataset.json
```

Generated evaluation output:

```text
evaluation_dataset_results.json
```

---

### POC Readiness Report

The readiness check validates whether the local demo is ready to present.

It checks:

- Backend API
- Ollama runtime
- Guardrail model availability
- Main model availability
- Audit logs
- Benchmark results
- Custom policy checker

---

### Full POC Governance Report Export

The report exporter combines:

- Model status
- Readiness report
- Model comparison rationale
- Evaluation dataset
- Benchmark results
- Dataset evaluation results
- Recent audit logs
- Governance summary

Exported report:

```text
layer3_full_poc_governance_report.json
```

---

## API Endpoints

| Endpoint | Purpose |
|---|---|
| `GET /health` | Backend health check |
| `GET /config` | Runtime configuration |
| `GET /models/status` | Ollama and model availability |
| `POST /pipeline/run` | Run guarded prompt pipeline |
| `GET /logs/recent` | View recent audit logs |
| `GET /logs/export` | Export audit logs |
| `POST /logs/clear` | Clear local audit logs |
| `GET /metrics/summary` | Runtime metrics summary |
| `POST /benchmark/run` | Run benchmark evaluation |
| `GET /poc/readiness` | Run POC readiness check |
| `GET /poc/model-comparison` | View architecture rationale |
| `GET /poc/export-report` | Export full POC report |
| `GET /dataset/list` | List evaluation dataset |
| `POST /dataset/add` | Add dataset test case |
| `DELETE /dataset/delete/{case_id}` | Delete dataset test case |
| `POST /dataset/reset` | Reset dataset |
| `POST /dataset/evaluate` | Evaluate dataset |

Swagger UI:

```text
http://127.0.0.1:8000/docs
```

---

## Quick Start

### 1. Start Ollama

Make sure Ollama is installed and running.

Required local models:

```powershell
ollama pull granite4.1-guardian:8b
ollama pull llama3.2
```

Check installed models:

```powershell
ollama list
```

---

### 2. Install Python dependencies

From this folder:

```powershell
cd Layer3-Classification-GuardRail/model-based-gpu-demo
pip install -r requirements.txt
```

---

### 3. Run the full demo

```powershell
.\run_all.ps1
```

This opens:

```text
Dashboard: http://127.0.0.1:5173
API Docs:   http://127.0.0.1:8000/docs
```

---

## Manual Run Commands

Backend:

```powershell
py -m uvicorn api:app --reload --port 8000
```

Frontend:

```powershell
cd ui
py -m http.server 5173
```

---

## Example Demo Flow

1. Open the dashboard.
2. Turn on Focus Mode.
3. Run a safe prompt.
4. Run a jailbreak prompt.
5. Load the custom company policy example.
6. Run the pipeline and show the custom policy block.
7. Run the readiness report.
8. Evaluate the dataset.
9. Export the full POC governance report.
10. Open Swagger and show the backend endpoints.

---

## Important Notes

This is a local POC, not a production safety system.

The benchmark and evaluation dataset are intentionally small and controlled. They are useful for proving the evaluation pipeline, API flow, logging, and dashboard behavior, but they are not a complete production-grade safety validation suite.

A production version would need:

- Larger evaluation datasets
- Human review workflows
- Persistent database storage
- Authentication and authorization
- Role-based access control
- Stronger audit retention
- Monitoring and alerting
- Deployment hardening
- Broader red-team testing

---

## Resume Summary

Built a local AI governance command center using FastAPI, Ollama, Granite Guardian 4.1 8B, and llama3.2 with input/output guardrails, custom company policy checks, risk scoring, audit logs, benchmark metrics, evaluation dataset management, readiness checks, and exportable governance reports.
