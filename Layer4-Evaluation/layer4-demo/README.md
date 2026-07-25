# Layer 4 Eval Gate — Demo

Semi-functioning demo of the Layer 4 architecture from the doc. Runs end to
end on your machine right now, no Docker/k8s/API keys required.

## Run it (pseudo-score mode, no setup needed)

```bash
pip install -r requirements.txt
python run.py --all
# or a single target:
python run.py --target support-chatbot-v3
python run.py --target kb-assistant-rag-v1
```

Outputs land in `reports/<target_id>.json` and `reports/<target_id>.html`.
Exit code is 0 (pass) or 1 (fail) — that's what a CI step or k8s Job would
check.

## Run it against a real, free, local LLM (--live)

This is the part that actually calls a model. It uses **Ollama** running
llama3.2 locally — free, no API key, runs on a laptop.

**One-time setup:**
```bash
# macOS
brew install ollama
ollama serve &              # starts the local server on :11434
ollama pull llama3.2:3b     # ~2GB, good balance of speed/quality for a demo judge

# Linux
curl -fsSL https://ollama.com/install.sh | sh
ollama serve &
ollama pull llama3.2:3b

# Windows: download the installer from https://ollama.com/download,
# it starts the server automatically after install
ollama pull llama3.2:3b
```

**Then run:**
```bash
python run.py --target support-chatbot-v3 --live
```

With `--live`, two things become real instead of stubbed:
1. **The attack transcripts** — each attacker prompt from
   `sample_transcripts.json` gets sent to your local llama3.2, and its
   real response replaces the canned one, before scoring runs.
2. **The deepeval OWASP metrics and RAGAS metrics** — instead of a hashed
   pseudo-score, the transcript + a scoring rubric get sent to llama3.2 as
   judge, asking it to return a JSON score. You'll see `[LIVE]` prefixed
   on the notes for any metric that got a real judge call.

If Ollama isn't running or the model isn't pulled, `--live` doesn't crash —
it prints a warning and falls back to pseudo-scores for that run, so the
demo still completes either way.

**Want an even lighter/faster model** for the judge (less accurate, but
fast on modest hardware): `ollama pull llama3.2:1b` then
`python run.py --target support-chatbot-v3 --live --model llama3.2:1b`.

Inspect AI and lm-eval-harness are **not** wired to Ollama — they stay as
deterministic pseudo-scores even with `--live`. Those two need their own
real frameworks installed (`pip install inspect-ai` / `pip install lm-eval`)
rather than a plain chat call, which is a separate follow-up.

## What's real vs. what's mocked

**Real, and this is the part worth reviewing:**
- The orchestrator → scorer → normalize → gate → report flow (`layer4/orchestrator.py`)
- The common `MetricResult` schema every tool's output gets flattened into (`layer4/schema.py`)
- RAGAS's conditional activation via `target_type: rag` in `targets.yaml`, checked in `RagasScorer.applies_to()`
- The PR-fast-subset vs. nightly-full-suite split for lm-eval-harness (`layer4/scorers/lm_eval_stub.py`)
- The `fail_under` threshold gate reading straight out of a YAML config, same shape as the real `deepeval: { owasp_llm_top10: true, fail_under: 0.85 }`
- The `used_llm_judge` flag on every metric — flows through to the report so you can see at a glance which scores came from an LLM call vs. a heuristic
- JSON output (Layer 5-ready) and HTML output (human-readable) from one shared report object

**Mocked without `--live`, real with it:**
- `BaseScorer._pseudo_score()` hashes the target + metric name into a deterministic fake score. With `--live`, deepeval's OWASP judge metrics and RAGAS's metrics use `layer4/llm_client.py` to call a real local Ollama model instead (`layer4/scorers/base.py: _judge_or_pseudo()`), falling back to the pseudo-score only if Ollama is unreachable.
- With `--live`, `layer4/live_attack.py` sends the sample attack prompts to the real local model and uses its actual response, instead of the canned one in `sample_transcripts.json`.

**Still mocked even with `--live`** (see "what I'd need" below):
- Inspect AI and lm-eval-harness stay pseudo-scored — they need their real frameworks installed, not just a chat call
- The judge is a local Ollama model, not routed through anything resembling your Layer 1 gateway — that architectural question is still open, this demo just makes the judge-call boundary visible (`used_llm_judge` + `[LIVE]` tags in the report) so it's easy to point real routing logic at later

## What I'd need from you to make each piece real

1. **A real target to hit.** A model endpoint (even a cheap one) behind
   something resembling your Layer 1 gateway, or just direct API access to
   swap in for `transcripts/sample_transcripts.json`.
2. **Actual deepeval + RAGAS installs.** Both are pip-installable
   (`pip install deepeval ragas`), but deepeval's OWASP metrics and RAGAS's
   faithfulness/relevancy metrics need an LLM judge — an API key (OpenAI,
   Anthropic, Gemini) or a locally-served model endpoint. Tell me which
   you want to use and I'll wire the real client in place of
   `_pseudo_score()`.
3. **Real Inspect AI tasks.** Either point me at existing `@task`
   definitions you have, or tell me which dangerous-capability categories
   to prioritize first and I'll draft the Inspect task/scorer pair.
4. **Real lm-eval-harness install** (`pip install lm-eval`) — this one
   needs no API key, just compute, so it's the easiest to make fully real.
   Tell me which tasks you actually want in the fast PR subset.
5. **Baseline data for thresholds.** Right now every `fail_under` in
   `targets.yaml` is a placeholder guess (this demo makes that obvious —
   both sample targets fail with plausible-looking scores against 0.85).
   A no-gate baseline sweep against your real target, even a small one,
   would let me set thresholds from actual numbers instead of guesses.
6. **Docker/k8s specifics**, if you want that part built too: your base
   image, registry, whether you want one combined image or four
   (deepeval + RAGAS do have overlapping dependency conflicts as noted in
   your doc — I can test that directly once I have both installed) and
   whatever Job/CronJob manifest conventions the rest of your cluster
   uses.

## Layout

```
layer4-demo/
  run.py                    # CLI entrypoint (what a k8s Job would exec)
  targets.yaml               # target registry incl. type: rag flag + thresholds
  transcripts/
    sample_transcripts.json  # mock Layer 2/3 scored attack transcripts
  layer4/
    schema.py                # common MetricResult / Layer4Report
    orchestrator.py           # dispatches to scorers, assembles report
    gate.py                    # pass/fail decision + CLI summary
    report.py                   # JSON + HTML writers
    scorers/
      base.py                   # shared interface, deterministic pseudo-scorer
      inspect_ai_stub.py
      lm_eval_stub.py
      deepeval_stub.py
      ragas_stub.py
  reports/                    # generated output (gitignored in a real repo)
```
