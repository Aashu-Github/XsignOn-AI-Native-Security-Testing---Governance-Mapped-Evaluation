import json
import re
import time
import requests
from datetime import datetime, timezone

OLLAMA_URL = "http://localhost:11434/api/generate"
GUARDRAIL_MODEL = "granite4.1-guardian:8b"

RISK_TYPES = [
    "jailbreak",
    "profanity",
    "violence",
    "harm"
]

def call_guardrail(prompt, risk_type):
    payload = {
        "model": GUARDRAIL_MODEL,
        "system": risk_type,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0,
            "num_ctx": 4096
        }
    }

    start = time.time()
    response = requests.post(OLLAMA_URL, json=payload, timeout=180)
    response.raise_for_status()
    data = response.json()
    latency = round(time.time() - start, 3)

    raw_response = data.get("response", "")
    thinking = data.get("thinking", "")

    match = re.search(r"<score>\s*(yes|no)\s*</score>", raw_response, re.IGNORECASE)
    score = match.group(1).lower() if match else "unknown"

    return {
        "risk_type": risk_type,
        "score": score,
        "blocked": score == "yes",
        "latency_seconds": latency,
        "raw_response": raw_response,
        "thinking_present": bool(thinking)
    }

def log_event(event):
    with open("gpu_guardrail_log.jsonl", "a", encoding="utf-8") as file:
        file.write(json.dumps(event) + "\n")

def main():
    print("Layer 3 GPU Guardrail Demo")
    print("Model:", GUARDRAIL_MODEL)
    print("Risks checked:", ", ".join(RISK_TYPES))
    print()

    prompt = input("User prompt: ").strip()

    if not prompt:
        print("No prompt entered.")
        return

    results = []

    for risk_type in RISK_TYPES:
        print(f"Checking {risk_type}...")
        result = call_guardrail(prompt, risk_type)
        results.append(result)

    blocked_risks = [r["risk_type"] for r in results if r["blocked"]]
    final_decision = "BLOCKED_BEFORE_MODEL" if blocked_risks else "ALLOWED"

    event = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "stage": "input_guardrail",
        "model": GUARDRAIL_MODEL,
        "prompt": prompt,
        "results": results,
        "blocked_risks": blocked_risks,
        "final_decision": final_decision
    }

    log_event(event)

    print()
    print("=== Guardrail Results ===")
    for result in results:
        print(f"{result['risk_type']}: score={result['score']} blocked={result['blocked']} latency={result['latency_seconds']}s")

    print()
    print("Blocked risks:", blocked_risks if blocked_risks else "None")
    print("Final decision:", final_decision)
    print("Saved log: gpu_guardrail_log.jsonl")

if __name__ == "__main__":
    main()
