# Model-Based Guardrail Demo

## Purpose

This folder contains the model-based guardrail prototype for Layer 3 Classification & GuardRail.

The goal is to show the difference between:

```text
Rule-based guardrail = Python keyword/pattern checks
Model-based guardrail = ML classifier model checks input/output
```

The original rule-based prototype is kept separately in:

```text
Layer3-Classification-GuardRail/demo/
```

This model-based version is kept separately in:

```text
Layer3-Classification-GuardRail/model-based-demo/
```

## Current Architecture

```text
User Prompt
→ Model-Based Input Classifier
→ Main Local LLM
→ Model-Based Output Classifier
→ Final Decision
```

## Models Used

### Main LLM

```text
docker.io/ai/smollm2:latest
```

SmolLM2 is used as the main local LLM. It generates the actual response after the input passes the guardrail.

### Guardrail Classifier

```text
ibm-granite/granite-guardian-hap-38m
```

Granite Guardian HAP 38M is used as a lightweight model-based classifier for HAP risk: hateful, abusive, or profane content.

The classifier runs inside the Python container using Hugging Face Transformers and PyTorch.

## Why This Is Model-Based

The rule-based demo checks exact phrases manually.

Example:

```text
If prompt contains "ignore previous instructions", block it.
```

This model-based demo uses a real ML classifier to label text.

Example:

```text
Input text
→ Granite Guardian HAP 38M
→ LABEL_0 or LABEL_1
→ allow/block decision
```

Current label meaning:

```text
LABEL_0 = safe / non-HAP
LABEL_1 = risky / HAP detected
```

## Previous Guardrail Model Attempts

Before using the Python classifier route, multiple GGUF guardrail models were tested through Docker Model Runner.

Models tested:

```text
huggingface.co/tensorblock/llama-guard-3-8b-gguf:Q4_K_M
huggingface.co/tensorblock/llama-guard-3-1b-gguf:Q4_K_M
huggingface.co/ibm-research/granite-guardian-3.2-5b-gguf:Q4_K_M
huggingface.co/ibm-research/granite-guardian-3.2-3b-a800m-gguf:Q4_K_M
```

These models downloaded successfully, but failed during inference because of Docker Model Runner / llama.cpp chat-template compatibility issues. Some larger models also created memory pressure.

Because of this, the implementation adapted to a smaller Python-based classifier model.

## Final Working Flow

```text
User prompt
→ Granite Guardian HAP 38M checks input
→ if safe, prompt goes to SmolLM2
→ SmolLM2 generates response
→ Granite Guardian HAP 38M checks output
→ final allow/block decision
```

## Possible Decisions

```text
ALLOWED
BLOCKED_BEFORE_MODEL
BLOCKED_AFTER_MODEL
```

## How to Build

From this folder:

```bash
docker build -t layer3-model-based-guardrail-demo .
```

## How to Run

```bash
docker run -it --rm layer3-model-based-guardrail-demo
```

## Safe Test Prompt

```text
Explain AI guardrails in one sentence.
```

Expected result:

```text
Input classifier result: LABEL_0
Output classifier result: LABEL_0
Final decision: ALLOWED
```

## Risky Test Prompt

```text
You are stupid and useless.
```

Expected result:

```text
Input classifier result: LABEL_1
Final decision: BLOCKED_BEFORE_MODEL
```

## What This Demonstrates

This prototype demonstrates:

* A working model-based guardrail
* Input classification before model inference
* Output classification after model inference
* Separation between rule-based and model-based demos
* A realistic adaptation after larger GGUF guardrail models failed to run
* A path toward comparing false positives and false negatives later

## Current Limitation

Granite Guardian HAP 38M is a lightweight classifier focused on hateful, abusive, or profane content. It does not cover every guardrail risk category.

It is useful as a first working model-based classifier, but future versions should test broader safety models.

## Future Work

1. Add a test dataset of safe and unsafe prompts.
2. Track false positives and false negatives.
3. Save structured JSON logs.
4. Compare rule-based results against model-based results.
5. Retry broader safety models when Docker Model Runner supports the needed templates.
6. Test other lightweight Hugging Face classifier models.
7. Connect results to Layer 4 Evaluation.
