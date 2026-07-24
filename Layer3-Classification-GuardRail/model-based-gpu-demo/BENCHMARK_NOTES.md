# GPU Guardrail Benchmark Notes

## Model

```text
granite4.1-guardian:8b
```

The model runs locally through Ollama on the Windows GPU system.

## Benchmark Scope

This benchmark is a small controlled test set designed to verify that the GPU-based guardrail pipeline works end-to-end.

It is not a production-grade benchmark yet.

## Risk Types Checked

```text
jailbreak
profanity
violence
harm
```

## Current Results

```text
Total tests: 8
Accuracy: 100.0%
Precision: 1.0
Recall: 1.0
F1 Score: 1.0
False Positive Rate: 0.0
False Negative Rate: 0.0
```

## What This Shows

The benchmark confirms that the larger GPU-based guardrail model can allow safe technical prompts and block direct jailbreaks, policy-bypass attempts, harmful requests, violent request prompts, and profane request prompts.

## Current Limitation

The benchmark is still small and controlled. A stronger evaluation should include paraphrased jailbreaks, indirect prompt injection, benign prompts that look suspicious, multi-turn attacks, RAG groundedness tests, answer relevance tests, tool-call hallucination tests, and latency measurements across more examples.

## Meeting Summary

This benchmark moves the project from a simple demo toward measurable guardrail evaluation. The current result proves that the GPU guardrail pipeline works locally and can produce accuracy, precision, recall, F1 score, false positive rate, and false negative rate.
