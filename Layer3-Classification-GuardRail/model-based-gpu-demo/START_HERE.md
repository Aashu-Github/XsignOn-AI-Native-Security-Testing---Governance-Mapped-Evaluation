# Start Here — Layer 3 AI Governance Command Center

This folder contains the GPU-based Layer 3 guardrail proof of concept.

It runs a local AI governance dashboard using:

- FastAPI backend
- Ollama local model runtime
- Granite Guardian guardrail model
- llama3.2 main model
- Premium HTML/CSS/JavaScript dashboard

---

## 1. Required Models

Make sure Ollama is installed and running.

Pull the required models:

```powershell
ollama pull granite4.1-guardian:8b
ollama pull llama3.2
```

Check installed models:

```powershell
ollama list
```

Expected models:

```text
granite4.1-guardian:8b
llama3.2
```

---

## 2. Install Dependencies

From this folder:

```powershell
pip install -r requirements.txt
```

---

## 3. Run Everything

Use the one-command launcher:

```powershell
.\run_all.ps1
```

This opens:

```text
Dashboard: http://127.0.0.1:5173
API Docs:   http://127.0.0.1:8000/docs
```

---

## 4. Best Demo Flow

Use this order for a clean walkthrough:

1. Open the dashboard.
2. Click **Focus Mode** for a cleaner demo view.
3. Run the safe prompt and show `ALLOWED`.
4. Load a jailbreak prompt and show blocking before the main model.
5. Click **Load Example Policy** and run it.
6. Show `BLOCKED_BEFORE_MODEL` with `custom_policy`.
7. Click **Readiness** and show `7/7`.
8. Scroll to the Evaluation Dataset Manager.
9. Click **Evaluate Dataset**.
10. Export the full POC governance report.
11. Open Swagger at `http://127.0.0.1:8000/docs`.

---

## 5. Important Dashboard Features

The dashboard includes:

- Input guardrail checks
- Output guardrail checks
- Custom company policy checking
- Risk scoring
- Severity visualization
- Decision trace timeline
- Live activity feed
- Runtime metrics
- Benchmark evaluation
- Evaluation dataset manager
- POC readiness report
- Audit logs
- Full governance report export
- Focus Mode for clean screenshots

---

## 6. Key Backend Endpoints

```text
GET    /health
GET    /config
GET    /models/status
POST   /pipeline/run
GET    /logs/recent
GET    /logs/export
POST   /logs/clear
GET    /metrics/summary
POST   /benchmark/run
GET    /poc/readiness
GET    /poc/model-comparison
GET    /poc/export-report
GET    /dataset/list
POST   /dataset/add
DELETE /dataset/delete/{case_id}
POST   /dataset/reset
POST   /dataset/evaluate
```

Swagger:

```text
http://127.0.0.1:8000/docs
```

---

## 7. Manual Run Commands

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

## 8. Generated Local Files

These files may be created during demos:

```text
gpu_guardrail_api_log.jsonl
benchmark_results.json
evaluation_dataset.json
evaluation_dataset_results.json
poc_report_export.json
```

Some generated result files are ignored by Git because they are local run artifacts.

---

## 9. What This POC Proves

This POC demonstrates how an AI system can add a governance layer around a main model.

The system can:

- Block unsafe prompts before model inference
- Review outputs before release
- Apply custom company-specific policies
- Log every decision as audit evidence
- Evaluate guardrail behavior with benchmark and dataset tools
- Export a full governance report for review

---

## 10. Production Notes

This is a local proof of concept, not a production safety system.

A production version would need:

- Larger red-team datasets
- Human review workflows
- Persistent database storage
- Authentication
- Role-based access control
- Strong audit retention
- Monitoring and alerting
- Deployment hardening
- Broader safety validation