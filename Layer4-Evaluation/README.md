# Layer 4 — Evaluation: Research & Questions

**Author:** Aashu Vadapalli  
**Date:** 2026-08-07  

---

## What Layer 4 Does

Layer 4 is the quality gate that runs after red-teaming (Layer 2) and guardrail classification (Layer 3). It takes scored attack transcripts and answers one question: does the model still behave well, or has something broken?

It runs in two modes: a **pre-deployment gate** that blocks bad versions from shipping, and **scheduled drift re-runs** that catch behavior changes after updates automatically.

Everything runs in Docker on Kubernetes (no VMs), so all tools need to be containerizable and stateless enough to run as k8s Jobs or CronJobs.

---

## Tools

| Tool | Who Made It | What It Does Here |
|------|-------------|-------------------|
| **Inspect AI** | UK AI Safety Institute | Safety and dangerous-capability evals |
| **lm-evaluation-harness** | EleutherAI | Capability and robustness baselines |
| **deepeval** | Confident AI | CI regression gates mapped to OWASP LLM Top 10 |
| **RAGAS** | Exploding Gradients | Groundedness and faithfulness for RAG targets only |

---

### Inspect AI

Safety-focused eval framework from AISI. You define a task (dataset + scorer), run it against the target via the Layer 1 gateway, and get a structured report back.

**Pros:** Built for safety eval with dangerous capability categories (cyberoffense, deception, etc.) that map directly to our MITRE ATLAS crosswalk. Reproducible by design since seeds, params, and transcripts are all logged. Runs headless in Docker without issues.

**Cons:** The `@task`/`@scorer` API has a learning curve for custom evals. Smaller community means fewer pre-built tasks. Reports need extra parsing to auto-feed into Layer 5. Mostly built for single-turn benchmarks, not multi-turn agentic scenarios.

---

### lm-evaluation-harness

Standard benchmark runner with 200+ pre-built tasks covering reasoning, math, coding, etc. We use it as a robustness baseline to catch if a security patch accidentally broke general model behavior.

**Pros:** Huge task library for instant baseline coverage. Outputs clean JSON that's easy to auto-ingest. Well-supported in Docker/HPC environments.

**Cons:** Not security-focused, so we'd need to write our own security tasks. Running everything on every PR would be too slow, so we'd need a scoped fast subset for CI and the full suite for nightly runs. Benchmark contamination is a concern if the target model trained on any of these datasets.

---

### deepeval

Basically pytest for LLM outputs. This is the actual CI gate. From `suite.yaml`: `deepeval: { owasp_llm_top10: true, fail_under: 0.85 }`. It blocks a merge if anything drops below threshold.

**Pros:** Drops into our existing pytest CI step. Pre-built metrics for OWASP LLM Top 10 with configurable `fail_under` per metric. Generates both HTML and JSON output.

**Cons:** Some metrics use an LLM-as-judge, which adds latency and cost to every CI run. The `0.85` threshold is a guess until we have baseline data to calibrate against. A few OWASP metrics are still thin, especially excessive agency.

---

### RAGAS

Only fires when the Layer 1 adapter identifies a RAG target. Measures faithfulness (did the answer come from retrieved docs?) and answer relevancy. Low faithfulness maps to OWASP LLM02 and LLM09.

**Pros:** The only tool here that natively understands RAG architecture. Faithfulness is a solid proxy for data leakage risk in knowledge-base chatbots. Lightweight and fast.

**Cons:** Zero value for non-RAG targets so conditional activation logic is needed. Also uses LLM-as-judge for some metrics. Metric definitions have shifted across versions, which can cause score drift even when the model hasn't changed.

---

## Questions for the Meet

1. **LLM-as-judge routing:** deepeval and RAGAS both call an LLM to score outputs. Should those calls go through the Layer 1 gateway (logged and auditable) or a local in-cluster model to keep costs down?

2. **Threshold calibration:** `fail_under: 0.85` assumes we know what 0.85 means for each metric. Do we have existing results to calibrate against, or do we run a no-gate baseline sweep first and set thresholds from real data?

3. **lm-evaluation-harness scope in CI:** What's the plan for PR checks vs. nightly? A fast subset for PRs and full suite overnight?

4. **RAGAS activation logic:** How does Layer 4 know a target is a RAG stack? Is there a `type: rag` field in the target config, or do we need to build that routing?

5. **Results normalization and image strategy:** Each tool outputs a different format, so do we normalize into a common schema before Layer 5 picks it up, and where does that happen? Related: RAGAS and deepeval have some overlapping dependency conflicts, so are we building one combined image or separate images per tool?
