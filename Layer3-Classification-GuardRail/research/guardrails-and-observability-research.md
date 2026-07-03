# Guardrails and Observability Research

## Purpose

This note summarizes the concepts from the video **“Guardrails and Observability for absolute Begineers”** and connects them to the Layer 3 Classification & GuardRail work.

The main idea is:

```text
Guardrails = enforce policy and control behavior
Observability = record, explain, measure, and audit behavior
```

A production AI system needs both.

## End-to-End Flow

```text
User input
-> input guardrail
-> main model / retrieval / tool execution
-> output guardrail
-> final response
-> logs, metrics, traces, evaluations, and audit evidence
```

## Guardrails

Guardrails are controls around the model. They can return actions such as:

```text
ALLOW
BLOCK
REDACT
REWRITE
REVIEW
REQUIRE_APPROVAL
```

### Input Guardrails

Run before the main model and can detect:

- Prompt injection and jailbreak attempts
- Requests for hidden instructions, credentials, or secrets
- Toxic or abusive content
- PII and sensitive data
- Out-of-scope topics
- Invalid formats or unsupported input
- Permission, tenant, and rate-limit violations

### Output Guardrails

Run after generation and can detect:

- Toxicity or harmful content
- Sensitive-information leakage
- Hallucination or unsupported claims
- Poor groundedness against retrieved context
- Policy or topic violations
- Invalid structured output

### Tool and Action Guardrails

For systems that use tools, guardrails should also enforce:

- Tool allowlists
- Least privilege
- Parameter validation
- Resource and retry budgets
- Human approval for high-impact actions
- Logging of the attempted and executed action

## Guardrail Approaches

| Approach | Main idea | Strength | Limitation |
|---|---|---|---|
| Rule-based | Keywords, regex, schemas, allow/deny lists | Fast and explainable | Misses paraphrases and context |
| Classifier-based | Trained model returns a label and score | Understands learned patterns | Coverage is limited to training categories |
| LLM-as-judge | Another LLM evaluates content | Flexible and policy-aware | Slower, costlier, and variable |
| Structured validation | JSON schema, types, ranges | Deterministic | Does not prove truth or safety |
| Human review | Person approves high-risk cases | Strong judgment | Slow and hard to scale |

## Observability

Observability means understanding the internal behavior of a system from the telemetry it emits.

### Monitoring vs Observability

```text
Monitoring: Is something wrong?
Observability: Why is it wrong?
```

### Core Signals

- **Logs:** event records, such as a guardrail block with category and reason
- **Metrics:** numeric measurements over time, such as block rate or p95 latency
- **Traces:** the complete path of a request through guardrails, models, retrieval, and tools

### Traces and Spans

```text
Trace: one end-to-end request
Span: one timed step inside the request
```

Example:

```text
Trace request-8f31
  input_guardrail       42 ms   ALLOW
  vector_retrieval      71 ms   4 documents
  main_model           480 ms   153 input / 62 output tokens
  output_guardrail      36 ms   ALLOW
  total                629 ms
```

## What to Record

A useful guardrail trace should include:

- Trace ID and timestamp
- Application and environment
- Pseudonymous user or tenant ID
- Main model and guardrail model names/versions
- Quantization or runtime configuration
- Prompt/template version
- Input and output token counts
- Time to first token and total latency
- Retrieval document IDs and relevance scores
- Tool calls and permission decisions
- Guardrail stage, category, score, threshold, decision, and reason
- Error, retry, fallback, and final outcome

## Privacy

Do not blindly store raw prompts and responses. Telemetry may contain PII, secrets, credentials, or proprietary information.

Use:

- Redaction
- Hashing or pseudonymous identifiers
- Encryption
- Access controls
- Retention limits
- Purpose-limited storage

## Guardrail Metrics

Track:

- Allow and block rates
- Blocks by category and stage
- False positives
- False negatives
- Precision, recall, and F1
- Attack success rate
- Guardrail latency
- Main-model p50/p95/p99 latency
- Token and cost usage
- Errors, timeouts, and fallbacks

## Thresholds

Classifier scores need policy thresholds.

```text
score >= 0.90 -> BLOCK
0.60 <= score < 0.90 -> REVIEW or REWRITE
score < 0.60 -> ALLOW
```

Thresholds must be tuned using a labeled evaluation set.

## Development Evaluation vs Runtime Guardrails

| Development evaluation | Runtime guardrail |
|---|---|
| Runs before release or on scheduled datasets | Runs on live requests |
| Measures quality and risk across many cases | Makes an immediate decision |
| Can use slower evaluators | Must meet latency budgets |
| Tunes policy and thresholds | Enforces policy |

## Application to Layer 3

Current repository components:

```text
Layer3-Classification-GuardRail/
  demo/               # rule-based guardrail
  model-based-demo/   # Granite Guardian HAP 38M classifier
  research/           # research notes
```

The current model-based demo proves input and output classification, but Granite Guardian HAP 38M is limited to hateful, abusive, and profane language. It does not provide complete coverage for prompt injection, jailbreaks, secrets, grounding, RAG risks, or tool misuse.

## Recommended Observability Addition

```text
Layer3-Classification-GuardRail/
  observability/
    event-schema.md
    sample-events.jsonl
    metrics.md
```

Example event:

```json
{
  "timestamp": "2026-07-03T12:34:56Z",
  "trace_id": "trace-8f31",
  "demo_type": "model_based",
  "stage": "input",
  "main_model": "smollm2",
  "guardrail_model": "granite-guardian-hap-38m",
  "category": "hap_toxicity",
  "label": "LABEL_1",
  "score": 0.997,
  "threshold": 0.50,
  "decision": "BLOCKED_BEFORE_MODEL",
  "latency_ms": 38,
  "reason": "HAP risk detected"
}
```

## Rule-Based vs Model-Based Observability

| Dimension | Rule-based demo | Model-based demo |
|---|---|---|
| Decision method | Explicit patterns | Learned classifier |
| Evidence | Matched rule | Label and score |
| Semantic understanding | Low | Higher within model scope |
| Latency | Very low | Higher |
| Main risk | Easy to bypass | Narrow or biased training coverage |

## Key Takeaways

1. Guardrails enforce; observability explains and measures.
2. Logs, metrics, and traces are all needed.
3. Record model versions, guardrail scores, thresholds, actions, and reasons.
4. Measure false positives and false negatives, not only total blocks.
5. Protect sensitive data inside telemetry.
6. The existing Layer 3 demos can gain observability without implementing an autonomous agent.

## Sources

- Video: https://www.youtube.com/watch?v=8E-zmt_JxDc
- OpenTelemetry Observability Primer: https://opentelemetry.io/docs/concepts/observability-primer/
- OpenTelemetry Overview: https://opentelemetry.io/docs/what-is-opentelemetry/
- LangSmith Observability: https://docs.langchain.com/langsmith/observability
- OWASP LLM Prompt Injection: https://genai.owasp.org/llmrisk/llm01-prompt-injection/
- OWASP Prompt Injection Prevention Cheat Sheet: https://cheatsheetseries.owasp.org/cheatsheets/LLM_Prompt_Injection_Prevention_Cheat_Sheet.html
- NIST AI RMF Generative AI Profile: https://www.nist.gov/publications/artificial-intelligence-risk-management-framework-generative-artificial-intelligence
- Granite Guardian HAP 38M: https://huggingface.co/ibm-granite/granite-guardian-hap-38m
