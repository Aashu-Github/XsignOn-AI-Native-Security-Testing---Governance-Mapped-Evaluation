import json
import requests
from datetime import datetime
from transformers import pipeline

MODEL_URL = "http://model-runner.docker.internal/engines/v1/chat/completions"
MAIN_MODEL = "docker.io/ai/smollm2:latest"

CLASSIFIER_MODEL = "ibm-granite/granite-guardian-hap-38m"

print("Loading classifier model...")
classifier = pipeline(
    "text-classification",
    model=CLASSIFIER_MODEL
)
print("Classifier loaded.")


def classify_with_model(text, stage):
    result = classifier(text)[0]

    label = result["label"]
    score = result["score"]

    # HAP means hateful/abusive/profane risk.
    # Depending on model label, risky text may be marked as LABEL_1 or toxic.
    risky_labels = ["LABEL_1", "toxic", "HAP", "hap"]

    is_risky = label in risky_labels

    return {
        "allowed": not is_risky,
        "stage": stage,
        "classifier_model": CLASSIFIER_MODEL,
        "label": label,
        "score": score,
        "category": "hap_toxicity_classifier",
        "reason": "Model-based classifier result from Granite Guardian HAP 38M."
    }


def call_main_model(prompt):
    payload = {
        "model": MAIN_MODEL,
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
    with open("model_based_guardrail_log.jsonl", "a") as file:
        file.write(json.dumps(record) + "\n")


def main():
    print("Layer 3 Model-Based Guardrail Demo")
    print("----------------------------------")
    print("Main LLM:", MAIN_MODEL)
    print("Classifier:", CLASSIFIER_MODEL)

    prompt = input("\nEnter test prompt: ")

    input_result = classify_with_model(prompt, "input")

    record = {
        "timestamp": datetime.now().isoformat(),
        "layer": "Layer3-Classification-GuardRail",
        "demo_type": "model_based_python_classifier",
        "main_model": MAIN_MODEL,
        "classifier_model": CLASSIFIER_MODEL,
        "input_prompt": prompt,
        "input_guardrail": input_result,
        "model_output": None,
        "output_guardrail": None,
        "final_decision": None
    }

    print("\nInput classifier result:")
    print(json.dumps(input_result, indent=2))

    if not input_result["allowed"]:
        record["final_decision"] = "BLOCKED_BEFORE_MODEL"
        log_decision(record)
        print("\nFinal decision: BLOCKED before reaching main model.")
        return

    model_output = call_main_model(prompt)
    record["model_output"] = model_output

    print("\nRaw main model output:")
    print(model_output)

    output_result = classify_with_model(model_output, "output")
    record["output_guardrail"] = output_result

    print("\nOutput classifier result:")
    print(json.dumps(output_result, indent=2))

    if not output_result["allowed"]:
        record["final_decision"] = "BLOCKED_AFTER_MODEL"
        log_decision(record)
        print("\nFinal decision: BLOCKED after model output.")
        return

    record["final_decision"] = "ALLOWED"
    log_decision(record)

    print("\nFinal safe output:")
    print(model_output)


if __name__ == "__main__":
    main()