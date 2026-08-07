# Architecture

```text
CSV or upstream cases
        |
        v
Target adapter (local reference / Gemini / Ollama / trace file)
        |
        v
Execution traces: input, retrieved context, output, timing, model metadata
        |
        +--> deterministic correctness and schema checks
        +--> privacy, medical-policy, hidden-context and unsafe-output checks
        +--> consistency checks
        +--> DeepEval (optional, real package)
        +--> RAGAS (optional, real package)
        |
        v
Metric results + OWASP GenAI/LLM Top 10 2026 mapping
        |
        +--> baseline regression comparison
        +--> human-vs-judge calibration
        |
        v
Gate verdict + JSONL evidence + HTML report
```

There are no hash-derived, random, canned, or pseudo evaluation scores. If an enabled external evaluator fails, the run records an evaluator error and a failed check instead of inventing a result.
