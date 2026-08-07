# Upstream trace schema

When Layers 2 and 3 are ready, set `target.provider` to `trace-file` and write one JSON object per line to `data/incoming_traces.jsonl`.

```json
{
  "case_id": "MED-00001-extract",
  "attempt": 1,
  "actual_output": "{\"patient_id\": \"MED-00001\", \"age\": 67}",
  "retrieved_contexts": [
    {
      "document_id": "record-MED-00001",
      "text": "{...record text...}",
      "metadata": {"source": "layer-3"}
    }
  ],
  "target_provider": "layer-3-guarded-model",
  "target_model": "model-name",
  "model_version": "sha256-or-release-id",
  "prompt_version": "prompt-v4",
  "retriever_version": "index-v2",
  "latency_ms": 842,
  "input_tokens": 320,
  "output_tokens": 55,
  "tool_calls": [],
  "error": null
}
```

The evaluation logic does not change when the trace source changes.
