import json
import requests
from datetime import datetime

MODEL_URL = "http://model-runner.docker.internal/engines/v1/chat/completions"
MODEL_NAME = "docker.io/ai/smollm2:latest"

BLOCKED_INPUT_PATTERNS = [
    "ignore previous instructions",
    "reveal your system prompt",
    "bypass safety",
    "disable guardrails",
    "secret key",
    "api key",
    "password"
]

BLOCKED_OUTPUT_PATTERNS = [
    "secret key",
    "api key",
    "password"
]

def classify_input(prompt):
    lowered = prompt.lower()

    for pattern in BLOCKED_INPUT_PATTERNS:
        if pattern in lowered:
            return {
                "allowed": False,
                "category": "prompt_injection_or_secret_request",
                "reason": f"Matched blocked input pattern: {pattern}"
            }

    return {
        "allowed": True,
        "category": "safe_or_low_risk",
        "reason": "No blocked input pattern matched."
    }

def classify_output(output):
    lowered = output.lower()

    for pattern in BLOCKED_OUTPUT_PATTERNS:
        if pattern in lowered:
            return {
                "allowed": False,
                "category": "sensitive_output_risk",
                "reason": f"Matched blocked output pattern: {pattern}"
            }

    return {
        "allowed": True,
        "category": "safe_or_low_risk",
        "reason": "No blocked output pattern matched."
    }

def call_model(prompt):
    payload = {
        "model": MODEL_NAME,
        "messages": [
            {
                "role": "system",
                "content": "You are a helpful assistant. Keep responses short, safe, and educational."
            },
            {
                "role": "user",
                "content": prompt
            }
        ]
    }

    response = requests.post(MODEL_URL, json=payload, timeout=60)
    response.raise_for_status()
    data = response.json()

    return data["choices"][0]["message"]["content"]

def log_decision(record):
    with open("guardrail_log.jsonl", "a") as file:
        file.write(json.dumps(record) + "\n")

def main():
    print("Layer 3 Classification & Guardrail Demo")
    print("---------------------------------------")
    prompt = input("Enter test prompt: ")

    input_result = classify_input(prompt)

    record = {
        "timestamp": datetime.now().isoformat(),
        "layer": "Layer3-Classification-GuardRail",
        "input_prompt": prompt,
        "input_guardrail": input_result,
        "model_used": MODEL_NAME,
        "model_output": None,
        "output_guardrail": None,
        "final_decision": None
    }

    print("\nInput classification:")
    print(json.dumps(input_result, indent=2))

    if not input_result["allowed"]:
        record["final_decision"] = "BLOCKED_BEFORE_MODEL"
        log_decision(record)
        print("\nFinal decision: BLOCKED before reaching model.")
        return

    model_output = call_model(prompt)
    record["model_output"] = model_output

    print("\nRaw model output:")
    print(model_output)

    output_result = classify_output(model_output)
    record["output_guardrail"] = output_result

    print("\nOutput classification:")
    print(json.dumps(output_result, indent=2))

    if not output_result["allowed"]:
        record["final_decision"] = "BLOCKED_AFTER_MODEL"
        log_decision(record)
        print("\nFinal decision: BLOCKED after model response.")
        return

    record["final_decision"] = "ALLOWED"
    log_decision(record)

    print("\nFinal safe output:")
    print(model_output)

if __name__ == "__main__":
    main()
