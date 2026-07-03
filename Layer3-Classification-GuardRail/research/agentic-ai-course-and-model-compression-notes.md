# Agentic AI Course and Model Compression Notes

**Video:** Complete Agentic AI Course - AI Agents, RAG, Embeddings, Architectures, Framework, VectorDB & Memory  
**Channel:** Tejas AI  
**Video URL:** https://www.youtube.com/watch?v=Pn95eOlw5qk

> Scope note: This is a structured explanation of the course's publicly listed concepts, supplemented with primary technical sources. It is not a verbatim transcript.

## Why this belongs in Layer 3

The course covers future surfaces that a Classification & GuardRail layer may need to inspect:

- user prompts and query interpretation
- retrieved RAG context
- tool calls and structured arguments
- model outputs
- memory writes
- inter-agent messages
- MCP tool/resource access
- logs, traces, and evaluation evidence

No autonomous agent implementation is required for the current internship work. These concepts help define what Layer 3 may eventually protect.

## Core agent model

```text
Goal
-> Interpret request
-> Read context/state/memory
-> Plan or choose next step
-> Select a tool
-> Execute through the orchestrator
-> Observe result
-> Verify
-> Update state
-> Continue, stop, or escalate
```

The LLM proposes decisions. Deterministic application code should validate schemas, enforce permissions, execute tools, manage retries, and record audit evidence.

## RAG, embeddings, and vector databases

RAG retrieves external evidence and adds it to the model context before generation.

```text
Documents -> chunk -> embed -> vector store
User query -> embed -> retrieve -> add context -> generate -> verify
```

Key Layer 3 risks:

- prompt injection inside retrieved documents
- unauthorized document retrieval
- irrelevant or poisoned chunks
- hallucinations beyond the retrieved evidence
- stale knowledge and missing provenance

Embeddings measure learned semantic similarity; they do not prove that a document is true or authorized. Vector databases should store metadata for source, owner, sensitivity, timestamp, and access policy.

## Memory and state

- **State:** current workflow data needed to continue a task.
- **Short-term memory:** current conversation, plan, and tool results.
- **Long-term memory:** facts, past events, preferences, and procedures saved for later.

Layer 3 should validate memory writes because memory can be poisoned, become stale, leak across users, or preserve sensitive data longer than intended.

## Tool use, MCP, and orchestration

Tools let a model interact with files, databases, APIs, search, or code. MCP standardizes how AI applications connect to external tools and data.

Guardrail controls should include:

- tool allowlists
- least-privilege credentials
- schema validation
- human approval for high-impact actions
- timeouts and rate limits
- output sanitization
- trace IDs and audit logging

## Structured communication

Agents commonly use JSON for tool calls, YAML for configuration, and XML for some integrations. Model-generated structured data must be parsed and validated before use. Unknown fields, wrong types, malformed documents, and unsafe commands should be rejected.

## Agent architectures covered conceptually

- **ReAct:** interleaves reasoning, action, and observation.
- **Plan-and-execute:** planner creates steps; executor performs them.
- **Reflection/Reflexion:** reviews failures and retries.
- **Graph/node workflow:** routes between explicit nodes and branches.
- **Multi-agent:** specialized agents communicate through structured messages.

Each architecture increases the need for traceability, stopping rules, permissions, and evaluation.

## Observability and evaluation

Recommended evidence fields:

- trace ID and timestamp
- model/version and prompt version
- retrieved document IDs and scores
- tool name, arguments, result, and status
- guardrail label/category/score
- final allow/block/escalate decision
- latency, throughput, tokens, and peak VRAM

Recommended metrics:

- false-negative rate
- false-positive rate
- category accuracy
- retrieval relevance and groundedness
- tool-call correctness
- latency and throughput
- peak GPU/CPU memory

## Windows GPU migration

The RTX 4070 SUPER has 12 GB GDDR6X. This makes CUDA-accelerated testing of larger guard models practical, especially when models are quantized.

Approximate raw weight memory:

| Model | FP16 | INT8 | INT4 |
|---|---:|---:|---:|
| 8B | ~16 GB | ~8 GB | ~4 GB |
| 13B | ~26 GB | ~13 GB | ~6.5 GB |
| 20B | ~40 GB | ~20 GB | ~10 GB |

Actual runtime use is higher because of KV cache, activations, context length, framework overhead, and batching.

## Model compression

### Quantization

Reduces numeric precision, for example FP16 to INT8 or INT4. This is the first technique to try for the RTX 4070 SUPER because it can allow an 8B guard model to fit in 12 GB VRAM.

### Pruning

Removes or masks less important weights or structures. Unstructured pruning does not always create real speedups unless the runtime supports sparsity. Structured pruning is more deployable but can remove useful capacity.

### Knowledge distillation

Trains a smaller student model to imitate a larger teacher. The student may retain strong task-specific behavior while losing some broad or rare-case capability.

### GGUF clarification

GGUF is a model file format used by llama.cpp. It is not itself the compression technique. Tags such as `Q4_K_M` describe the quantization stored inside the GGUF file.

## Does compression reduce performance?

It can. The effect depends on model, task, method, and compression level.

- FP16/BF16: generally minimal inference loss.
- INT8: often a small loss.
- INT4: much smaller memory use, but some tasks and models lose accuracy.
- 2-3 bit: greater chance of noticeable degradation.
- pruning: may remove useful capacity.
- distillation: may preserve the target task while losing breadth.

For a guardrail, evaluate compressed models carefully because small average-quality losses may increase unsafe false negatives or unnecessary false positives.

## Recommended next experiment

Keep the current two baselines unchanged:

```text
demo/               rule-based classifier
model-based-demo/   Granite Guardian HAP 38M classifier
```

Create a separate Windows/GPU experiment later, for example:

```text
gpu-model-based-demo/
```

Compare a broader Llama Guard or Granite Guardian model at higher precision vs 8-bit vs 4-bit using the same labeled test set. Record false negatives, false positives, latency, throughput, and peak VRAM.

## Sources

1. Tejas AI course video: https://www.youtube.com/watch?v=Pn95eOlw5qk
2. Lewis et al., Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks, arXiv:2005.11401.
3. Yao et al., ReAct: Synergizing Reasoning and Acting in Language Models, arXiv:2210.03629.
4. Model Context Protocol official documentation.
5. Hugging Face Transformers quantization documentation.
6. PyTorch pruning tutorial.
7. Hinton, Vinyals, and Dean, Distilling the Knowledge in a Neural Network.
8. NVIDIA GeForce RTX 4070 family specifications.
9. IBM Granite Guardian HAP 38M and Granite Guardian 3.2 model cards.
10. Meta Llama Guard 3 model card and Llama Guard paper.
