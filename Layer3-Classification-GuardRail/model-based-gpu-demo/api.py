import json
import re
import time
import requests
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel


OLLAMA_URL = "http://localhost:11434/api/generate"

DEFAULT_GUARDRAIL_MODEL = "granite4.1-guardian:8b"
DEFAULT_MAIN_MODEL = "llama3.2"

ALLOWED_RISK_TYPES = [
    "jailbreak",
    "profanity",
    "violence",
    "harm"
]


app = FastAPI(
    title="Layer 3 GPU Guardrail API",
    description="Input/output guardrail API using Granite Guardian 4.1 8B and a local main LLM.",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class PipelineRequest(BaseModel):
    prompt: str
    guardrail_model: str = DEFAULT_GUARDRAIL_MODEL
    main_model: str = DEFAULT_MAIN_MODEL
    risk_types: Optional[List[str]] = None
    temperature: float = 0.0
    num_ctx: int = 4096
    enable_input_guardrail: bool = True
    enable_output_guardrail: bool = True
    logging_enabled: bool = True


def call_ollama(model: str, prompt: str, system: Optional[str] = None, temperature: float = 0.0, num_ctx: int = 4096):
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": temperature,
            "num_ctx": num_ctx
        }
    }

    if system:
        payload["system"] = system

    start = time.time()

    try:
        response = requests.post(OLLAMA_URL, json=payload, timeout=240)
        response.raise_for_status()
    except requests.exceptions.RequestException as error:
        raise HTTPException(status_code=500, detail=f"Ollama request failed: {error}")

    data = response.json()
    latency = round(time.time() - start, 3)

    return data, latency


def extract_score(text: str):
    match = re.search(r"<score>\s*(yes|no)\s*</score>", text, re.IGNORECASE)

    if not match:
        return "unknown"

    return match.group(1).lower()


def run_single_guardrail_check(text: str, risk_type: str, stage: str, guardrail_model: str, num_ctx: int):
    data, latency = call_ollama(
        model=guardrail_model,
        system=risk_type,
        prompt=text,
        temperature=0.0,
        num_ctx=num_ctx
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


def run_guardrail_checks(text: str, stage: str, risk_types: List[str], guardrail_model: str, num_ctx: int):
    results = []

    for risk_type in risk_types:
        result = run_single_guardrail_check(
            text=text,
            risk_type=risk_type,
            stage=stage,
            guardrail_model=guardrail_model,
            num_ctx=num_ctx
        )
        results.append(result)

    blocked_risks = [result["risk_type"] for result in results if result["blocked"]]

    return results, blocked_risks


def call_main_model(prompt: str, main_model: str, temperature: float, num_ctx: int):
    data, latency = call_ollama(
        model=main_model,
        system="You are a helpful assistant. Keep responses concise, safe, and clear.",
        prompt=prompt,
        temperature=temperature,
        num_ctx=num_ctx
    )

    return {
        "model": main_model,
        "response": data.get("response", ""),
        "latency_seconds": latency
    }


def log_event(event):
    with open("gpu_guardrail_api_log.jsonl", "a", encoding="utf-8") as file:
        file.write(json.dumps(event) + "\n")


@app.get("/")
def root():
    return {
        "message": "Layer 3 GPU Guardrail API is running",
        "guardrail_model": DEFAULT_GUARDRAIL_MODEL,
        "main_model": DEFAULT_MAIN_MODEL
    }


@app.get("/health")
def health():
    return {
        "status": "ok",
        "ollama_url": OLLAMA_URL,
        "guardrail_model": DEFAULT_GUARDRAIL_MODEL,
        "main_model": DEFAULT_MAIN_MODEL
    }


@app.get("/config")
def config():
    return {
        "allowed_risk_types": ALLOWED_RISK_TYPES,
        "safe_client_controls": [
            "temperature",
            "num_ctx",
            "main_model",
            "guardrail_model",
            "risk_types",
            "enable_input_guardrail",
            "enable_output_guardrail",
            "logging_enabled"
        ]
    }


@app.post("/pipeline/run")
def run_pipeline(request: PipelineRequest):
    if not request.prompt.strip():
        raise HTTPException(status_code=400, detail="Prompt cannot be empty.")

    risk_types = request.risk_types or ALLOWED_RISK_TYPES

    invalid_risks = [risk for risk in risk_types if risk not in ALLOWED_RISK_TYPES]

    if invalid_risks:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid risk types: {invalid_risks}. Allowed: {ALLOWED_RISK_TYPES}"
        )

    start_total = time.time()

    input_results = []
    input_blocked_risks = []

    if request.enable_input_guardrail:
        input_results, input_blocked_risks = run_guardrail_checks(
            text=request.prompt,
            stage="input",
            risk_types=risk_types,
            guardrail_model=request.guardrail_model,
            num_ctx=request.num_ctx
        )

    if input_blocked_risks:
        final_decision = "BLOCKED_BEFORE_MODEL"

        event = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "pipeline": "layer3_gpu_guardrail_api",
            "prompt": request.prompt,
            "input_guardrail_results": input_results,
            "input_blocked_risks": input_blocked_risks,
            "main_model_result": None,
            "output_guardrail_results": None,
            "output_blocked_risks": None,
            "final_decision": final_decision,
            "total_latency_seconds": round(time.time() - start_total, 3)
        }

        if request.logging_enabled:
            log_event(event)

        return event

    main_model_result = call_main_model(
        prompt=request.prompt,
        main_model=request.main_model,
        temperature=request.temperature,
        num_ctx=request.num_ctx
    )

    output_results = []
    output_blocked_risks = []

    if request.enable_output_guardrail:
        output_results, output_blocked_risks = run_guardrail_checks(
            text=main_model_result["response"],
            stage="output",
            risk_types=risk_types,
            guardrail_model=request.guardrail_model,
            num_ctx=request.num_ctx
        )

    if output_blocked_risks:
        final_decision = "BLOCKED_AFTER_MODEL"
        final_response = "[BLOCKED] The model output was blocked by the output guardrail."
    else:
        final_decision = "ALLOWED"
        final_response = main_model_result["response"]

    event = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "pipeline": "layer3_gpu_guardrail_api",
        "prompt": request.prompt,
        "input_guardrail_results": input_results,
        "input_blocked_risks": input_blocked_risks,
        "main_model_result": main_model_result,
        "output_guardrail_results": output_results,
        "output_blocked_risks": output_blocked_risks,
        "final_decision": final_decision,
        "final_response": final_response,
        "total_latency_seconds": round(time.time() - start_total, 3)
    }

    if request.logging_enabled:
        log_event(event)

    return event