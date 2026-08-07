from __future__ import annotations

import argparse
import json
import mimetypes
import threading
import traceback
import urllib.parse
import webbrowser
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from layer4.config import ROOT, deep_merge, load_config
from layer4.orchestrator import EvaluationOrchestrator
from layer4.metric_catalog import DEFAULT_ENABLED_METRICS, METRIC_CATALOG, normalize_enabled_metrics
from layer4.storage import RunStorage


class JobManager:
    def __init__(self, base_config: dict[str, Any]):
        self.base_config = base_config
        self.storage = RunStorage()
        self.jobs: dict[str, dict[str, Any]] = {}
        self.lock = threading.Lock()

    def create(self, overrides: dict[str, Any]) -> str:
        import uuid
        from datetime import datetime, timezone

        run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:8]
        config = deep_merge(self.base_config, overrides)
        with self.lock:
            self.jobs[run_id] = {
                "run_id": run_id,
                "status": "queued",
                "stage": "queued",
                "progress": 0,
                "message": "Queued",
                "report": None,
                "error": None,
            }
        thread = threading.Thread(target=self._run, args=(run_id, config), daemon=True)
        thread.start()
        return run_id

    def _run(self, run_id: str, config: dict[str, Any]) -> None:
        def progress(update: dict[str, Any]) -> None:
            with self.lock:
                self.jobs[run_id].update(update)
                self.jobs[run_id]["status"] = "running" if update.get("stage") != "complete" else "complete"

        try:
            report = EvaluationOrchestrator(config, storage=self.storage).run(run_id=run_id, progress=progress)
            with self.lock:
                self.jobs[run_id].update({"status": "complete", "progress": 100, "report": report})
        except Exception as exc:
            with self.lock:
                self.jobs[run_id].update({
                    "status": "failed",
                    "stage": "failed",
                    "message": str(exc),
                    "error": f"{type(exc).__name__}: {exc}\n{traceback.format_exc()}",
                })

    def get(self, run_id: str) -> dict[str, Any] | None:
        with self.lock:
            job = self.jobs.get(run_id)
            if job:
                return dict(job)
        report = self.storage.load_report(run_id)
        if report:
            return {"run_id": run_id, "status": "complete", "stage": "complete", "progress": 100, "report": report}
        return None


class Layer4RequestHandler(BaseHTTPRequestHandler):
    server_version = "XSignOnLayer4/1.0"

    @property
    def app(self) -> "Layer4WebServer":
        return self.server.app  # type: ignore[attr-defined]

    def log_message(self, fmt: str, *args: Any) -> None:
        print(f"[web] {self.address_string()} - {fmt % args}")

    def _send_json(self, payload: Any, status: int = 200) -> None:
        body = json.dumps(payload, ensure_ascii=False, default=str).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _send_file(self, path: Path) -> None:
        if not path.exists() or not path.is_file():
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        body = path.read_bytes()
        content_type = mimetypes.guess_type(str(path))[0] or "application/octet-stream"
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_json(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length) if length else b"{}"
        return json.loads(raw.decode("utf-8"))

    def do_GET(self) -> None:  # noqa: N802
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        if path == "/":
            return self._send_file(ROOT / "web" / "index.html")
        if path in {"/metrics", "/metrics/"}:
            return self._send_file(ROOT / "web" / "metrics.html")
        if path.startswith("/static/"):
            relative = Path(path.removeprefix("/static/"))
            candidate = (ROOT / "web" / relative).resolve()
            if ROOT / "web" not in candidate.parents:
                return self.send_error(HTTPStatus.FORBIDDEN)
            return self._send_file(candidate)
        if path == "/api/metrics":
            return self._send_json({
                "catalog": METRIC_CATALOG,
                "default_enabled": self.app.base_config.get("metrics", {}).get("enabled", DEFAULT_ENABLED_METRICS),
                "mandatory_system_checks": [
                    {"id": "target_execution", "description": "Always active so a target connection failure cannot be hidden."},
                    {"id": "judge_library_availability", "description": "Active when selected DeepEval or RAGAS metrics require a library or judge."},
                ],
            })
        if path == "/api/config":
            safe_config = json.loads(json.dumps(self.app.base_config))
            safe_config["environment"] = {
                "gemini_key_set": bool(__import__("os").environ.get("GEMINI_API_KEY")),
                "openai_key_set": bool(__import__("os").environ.get("OPENAI_API_KEY")),
            }
            return self._send_json(safe_config)
        if path == "/api/runs":
            return self._send_json({"runs": self.app.jobs.storage.list_runs(), "baseline_run_id": self.app.jobs.storage.get_baseline_id()})
        if path.startswith("/api/run/"):
            run_id = path.split("/")[-1]
            job = self.app.jobs.get(run_id)
            return self._send_json(job or {"error": "Run not found"}, 200 if job else 404)
        if path.startswith("/reports/"):
            parts = path.strip("/").split("/")
            if len(parts) == 3 and parts[2] in {"report.html", "report.json", "cases.jsonl", "traces.jsonl", "metrics.jsonl"}:
                run_id = parts[1]
                return self._send_file(self.app.jobs.storage.reports_root / run_id / parts[2])
        if path == "/api/health":
            return self._send_json({"status": "ok"})
        self.send_error(HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:  # noqa: N802
        parsed = urllib.parse.urlparse(self.path)
        try:
            payload = self._read_json()
        except Exception as exc:
            return self._send_json({"error": f"Invalid JSON: {exc}"}, 400)

        if parsed.path == "/api/run":
            target_provider = str(payload.get("target_provider", "ollama"))
            target_default_model = "llama3.2:latest" if target_provider == "ollama" else "local-record-v1"
            target = {
                "provider": target_provider,
                "model": payload.get("target_model") or target_default_model,
                "base_url": payload.get("target_base_url", "http://localhost:11434"),
                "temperature": float(payload.get("temperature", 0.0)),
            }
            judge = {
                "provider": payload.get("judge_provider", "gemini"),
                "model": payload.get("judge_model", "gemini-3.6-flash"),
                "enable_deepeval": bool(payload.get("enable_deepeval", False)),
                "enable_ragas": bool(payload.get("enable_ragas", False)),
                "max_cases": max(1, min(100, int(payload.get("judge_max_cases", 8)))),
            }
            run = {
                "max_records": max(1, min(100, int(payload.get("max_records", 6)))),
                "repeat_count": max(1, min(10, int(payload.get("repeat_count", 1)))),
                "seed": int(payload.get("seed", 42)),
            }
            try:
                enabled_metrics = normalize_enabled_metrics(payload.get("enabled_metrics"))
            except ValueError as exc:
                return self._send_json({"error": str(exc)}, 400)
            if not enabled_metrics:
                return self._send_json({"error": "Select at least one evaluation metric."}, 400)
            run_id = self.app.jobs.create({
                "target": target,
                "judge": judge,
                "run": run,
                "metrics": {"enabled": enabled_metrics},
            })
            return self._send_json({"run_id": run_id, "status": "queued"}, 202)

        if parsed.path == "/api/baseline":
            run_id = str(payload.get("run_id", ""))
            try:
                self.app.jobs.storage.set_baseline(run_id)
            except Exception as exc:
                return self._send_json({"error": str(exc)}, 400)
            return self._send_json({"status": "ok", "baseline_run_id": run_id})

        self.send_error(HTTPStatus.NOT_FOUND)


class Layer4WebServer(ThreadingHTTPServer):
    def __init__(self, address: tuple[str, int], handler, base_config: dict[str, Any]):
        super().__init__(address, handler)
        self.app = self
        self.base_config = base_config
        self.jobs = JobManager(base_config)


def serve(host: str = "127.0.0.1", port: int = 8080, open_browser: bool = True) -> None:
    config = load_config()
    server = Layer4WebServer((host, port), Layer4RequestHandler, config)
    url = f"http://{host}:{port}"
    print(f"XSignOn Layer 4 dashboard: {url}")
    print("Press Ctrl+C to stop.")
    if open_browser:
        threading.Timer(0.7, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping server.")
    finally:
        server.server_close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the XSignOn Layer 4 local dashboard")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args()
    serve(args.host, args.port, not args.no_browser)


if __name__ == "__main__":
    main()
