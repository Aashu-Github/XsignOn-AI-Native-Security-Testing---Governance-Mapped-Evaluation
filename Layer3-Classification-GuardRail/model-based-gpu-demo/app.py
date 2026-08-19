import json
import re
import time
import requests
from datetime import datetime, timezone

OLLAMA_URL = "http://localhost:11434/api/generate"

GUARDRAIL_MODEL = "granite4.1-guardian:8b"
MAIN_MODEL = "llama3.2"

RISK_TYPES = [
    "jailbreak",
    "profanity",
    "violence",
    "harm"
]


def call_ollama(model, prompt, system=None, timeout=180):
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0,
            "num_ctx": 4096
        }
    }

    if system:
        payload["system"] = system

    start = time.time()
    response = requests.post(OLLAMA_URL, json=payload, timeout=timeout)
    response.raise_for_status()
    data = response.json()
    latency = round(time.time() - start, 3)

    return data, latency


def extract_score(text):
    match = re.search(r"<score>\s*(yes|no)\s*</score>", text, re.IGNORECASE)

    if not match:
        return "unknown"

    return match.group(1).lower()


def call_guardrail(text, risk_type, stage):
    data, latency = call_ollama(
        model=GUARDRAIL_MODEL,
        system=risk_type,
        prompt=text
    )

    raw_response = data.get("response", "")
    score = extract_score(raw_response)

    return {
        "stage": stage,
        "risk_type": risk_type,
        "score": score,
        "blocked": score == "yes",
        "latency_seconds": latency,
        "raw_response": raw_response
    }


def run_guardrail_checks(text, stage):
    results = []

    for risk_type in RISK_TYPES:
        print(f"Checking {stage} {risk_type}...")
        result = call_guardrail(text, risk_type, stage)
        results.append(result)

    blocked_risks = [r["risk_type"] for r in results if r["blocked"]]

    return results, blocked_risks


def call_main_model(user_prompt):
    data, latency = call_ollama(
        model=MAIN_MODEL,
        system="You are a helpful assistant. Keep answers concise and safe.",
        prompt=user_prompt
    )

    return {
        "model": MAIN_MODEL,
        "response": data.get("response", ""),
        "latency_seconds": latency
    }


def log_event(event):
    with open("gpu_guardrail_log.jsonl", "a", encoding="utf-8") as file:
        file.write(json.dumps(event) + "\n")


def main():
    print("Layer 3 GPU Guardrail Full Pipeline")
    print("Guardrail model:", GUARDRAIL_MODEL)
    print("Main model:", MAIN_MODEL)
    print("Risks checked:", ", ".join(RISK_TYPES))
    print()

    user_prompt = input("User prompt: ").strip()

    if not user_prompt:
        print("No prompt entered.")
        return

    print()
    print("=== Step 1: Input Guardrail ===")
    input_results, input_blocked_risks = run_guardrail_checks(
        text=user_prompt,
        stage="input"
    )

    if input_blocked_risks:
        final_decision = "BLOCKED_BEFORE_MODEL"

        event = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "pipeline": "gpu_guardrail_full_pipeline",
            "user_prompt": user_prompt,
            "input_guardrail_results": input_results,
            "input_blocked_risks": input_blocked_risks,
            "main_model_result": None,
            "output_guardrail_results": None,
            "output_blocked_risks": None,
            "final_decision": final_decision
        }

        log_event(event)

        print()
        print("=== Final Result ===")
        print("Input blocked risks:", input_blocked_risks)
        print("Final decision:", final_decision)
        print("Saved log: gpu_guardrail_log.jsonl")
        return

    print()
    print("Input allowed. Sending prompt to main LLM...")

    print()
    print("=== Step 2: Main LLM ===")
    main_model_result = call_main_model(user_prompt)
    model_output = main_model_result["response"]

    print("Main model response:")
    print(model_output)

    print()
    print("=== Step 3: Output Guardrail ===")
    output_results, output_blocked_risks = run_guardrail_checks(
        text=model_output,
        stage="output"
    )

    if output_blocked_risks:
        final_decision = "BLOCKED_AFTER_MODEL"
        final_response = "[BLOCKED] The model output was blocked by the output guardrail."
    else:
        final_decision = "ALLOWED"
        final_response = model_output

    event = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "pipeline": "gpu_guardrail_full_pipeline",
        "user_prompt": user_prompt,
        "input_guardrail_results": input_results,
        "input_blocked_risks": input_blocked_risks,
        "main_model_result": main_model_result,
        "output_guardrail_results": output_results,
        "output_blocked_risks": output_blocked_risks,
        "final_decision": final_decision,
        "final_response": final_response
    }

    log_event(event)

    print()
    print("=== Final Result ===")
    print("Output blocked risks:", output_blocked_risks if output_blocked_risks else "None")
    print("Final decision:", final_decision)
    print()
    print("Final response:")
    print(final_response)
    print()
    print("Saved log: gpu_guardrail_log.jsonl")


if __name__ == "__main__":
    main()