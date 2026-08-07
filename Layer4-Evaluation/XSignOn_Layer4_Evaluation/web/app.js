"use strict";

const $ = (id) => document.getElementById(id);

const METRIC_STORAGE_KEY = "xsignon-layer4-enabled-metrics-v1";

const state = {
  activeRun: null,
  baselineRunId: null,
  config: null,
  pollTimer: null,
  metricCatalog: [],
  enabledMetrics: [],
};

const PROVIDER_DEFAULTS = {
  "local-record": {
    model: "local-record-v1",
    hint: "Reference target included with the package.",
    label: "Local record",
  },
  ollama: {
    model: "llama3.2:latest",
    hint: "Use the exact name shown by `ollama list`.",
    label: "Ollama",
  },
  gemini: {
    model: "gemini-3.6-flash",
    hint: "Requires GEMINI_API_KEY in the server environment.",
    label: "Gemini",
  },
  "trace-file": {
    model: "upstream-trace",
    hint: "Reads the configured incoming trace JSONL file.",
    label: "Trace file",
  },
};

const JUDGE_DEFAULTS = {
  ollama: "llama3.2:latest",
  gemini: "gemini-3.6-flash",
  "openai-default": "gpt-4.1-mini",
};

function escapeHTML(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function safeClass(value) {
  return String(value ?? "unknown").replace(/[^a-zA-Z0-9_-]/g, "-");
}

function fmt(value, digits = 3) {
  if (value === null || value === undefined || Number.isNaN(value)) return "—";
  return typeof value === "number" ? value.toFixed(digits) : String(value);
}

function fmtPercent(value) {
  if (value === null || value === undefined || Number.isNaN(value)) return "—";
  const normalized = Number(value) <= 1 ? Number(value) * 100 : Number(value);
  return `${normalized.toFixed(1)}%`;
}

function fmtDate(value) {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return String(value);
  return new Intl.DateTimeFormat(undefined, {
    year: "numeric",
    month: "short",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  }).format(date);
}

function toast(message, type = "info", title = type === "error" ? "Something went wrong" : "Layer 4") {
  const region = $("toastRegion");
  const item = document.createElement("div");
  item.className = `toast ${safeClass(type)}`;
  item.innerHTML = `
    <div>
      <strong>${escapeHTML(title)}</strong>
      <p>${escapeHTML(message)}</p>
    </div>
    <button type="button" aria-label="Dismiss notification">×</button>
  `;

  const dismiss = () => item.remove();
  item.querySelector("button").addEventListener("click", dismiss);
  region.appendChild(item);
  window.setTimeout(dismiss, type === "error" ? 9000 : 5000);
}

async function api(path, options = {}) {
  const headers = new Headers(options.headers || {});
  if (options.body && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  const response = await fetch(path, {
    cache: "no-store",
    ...options,
    headers,
  });

  const contentType = response.headers.get("content-type") || "";
  let body;
  if (contentType.includes("application/json")) {
    body = await response.json();
  } else {
    const text = await response.text();
    body = { error: text || `Request failed: ${response.status}` };
  }

  if (!response.ok) {
    throw new Error(body.error || `Request failed: ${response.status}`);
  }
  return body;
}

function setRunButton(running) {
  const button = $("runButton");
  button.disabled = running;
  button.classList.toggle("is-running", running);
  button.querySelector(".button-label").textContent = running ? "Running evaluation" : "Run evaluation";
}

function updateHeroSummary() {
  const provider = $("targetProvider").value;
  const model = $("targetModel").value.trim();
  const label = PROVIDER_DEFAULTS[provider]?.label || provider;
  $("heroTarget").textContent = model ? `${label} · ${model}` : label;

  const enabled = [];
  if ($("enableDeepEval").checked) enabled.push("DeepEval");
  if ($("enableRagas").checked) enabled.push("RAGAS");
  $("heroJudges").textContent = enabled.length ? enabled.join(" + ") : "Core evaluators";
}

function updateJudgeUI() {
  const deepEval = $("enableDeepEval");
  const ragas = $("enableRagas");
  const enabled = deepEval.checked || ragas.checked;
  $("judgeBlock").classList.toggle("enabled", enabled);

  document.querySelectorAll(".toggle-card").forEach((card) => {
    const input = card.querySelector('input[type="checkbox"]');
    card.classList.toggle("active", Boolean(input?.checked));
  });

  $("judgeProvider").disabled = !enabled;
  $("judgeModel").disabled = !enabled;
  $("judgeMaxCases").disabled = !enabled;
  updateHeroSummary();
}

function applyProviderDefaults({ force = true } = {}) {
  const provider = $("targetProvider").value;
  const defaults = PROVIDER_DEFAULTS[provider];
  if (!defaults) return;

  if (force || !$("targetModel").value.trim()) {
    $("targetModel").value = defaults.model;
  }
  $("targetModelHint").textContent = defaults.hint;
  updateHeroSummary();
}

function applyJudgeDefaults({ force = true } = {}) {
  const provider = $("judgeProvider").value;
  if (force && JUDGE_DEFAULTS[provider]) {
    $("judgeModel").value = JUDGE_DEFAULTS[provider];
  }
  updateHeroSummary();
}

function readStoredMetrics(defaults = []) {
  try {
    const parsed = JSON.parse(localStorage.getItem(METRIC_STORAGE_KEY) || "null");
    if (Array.isArray(parsed)) return parsed.map(String);
  } catch (_) {
    // Ignore malformed browser storage and use server defaults.
  }
  return [...defaults];
}

async function loadMetricSelection() {
  const data = await api("/api/metrics");
  state.metricCatalog = data.catalog || [];
  const validIds = new Set(state.metricCatalog.map((item) => item.id));
  const defaults = data.default_enabled || state.metricCatalog.map((item) => item.id);
  state.enabledMetrics = readStoredMetrics(defaults).filter((id) => validIds.has(id));
  if (!state.enabledMetrics.length) state.enabledMetrics = [...defaults];
  localStorage.setItem(METRIC_STORAGE_KEY, JSON.stringify(state.enabledMetrics));

  const count = state.enabledMetrics.length;
  const total = state.metricCatalog.length;
  if ($("selectedMetricCount")) $("selectedMetricCount").textContent = `${count} of ${total} metrics tested`;
  if ($("selectedMetricNames")) {
    const disabled = state.metricCatalog.filter((item) => !state.enabledMetrics.includes(item.id));
    $("selectedMetricNames").textContent = disabled.length
      ? `Not tested: ${disabled.map((item) => item.label).join(", ")}`
      : "All selectable metrics are tested.";
  }
}

async function loadConfig() {
  const config = await api("/api/config");
  state.config = config;

  const env = config.environment || {};
  const statusText = env.gemini_key_set
    ? "Gemini key detected"
    : env.openai_key_set
      ? "OpenAI key detected"
      : "Local core mode ready";
  $("environmentStatus").lastElementChild.textContent = statusText;

  const target = config.target || {};
  const run = config.run || {};
  const judge = config.judge || {};

  if (target.provider && $("targetProvider").querySelector(`option[value="${CSS.escape(target.provider)}"]`)) {
    $("targetProvider").value = target.provider;
  }
  $("targetModel").value = target.model || PROVIDER_DEFAULTS[$("targetProvider").value].model;
  $("targetBaseUrl").value = target.base_url || "http://localhost:11434";
  $("maxRecords").value = run.max_records ?? 6;
  $("repeatCount").value = run.repeat_count ?? 1;
  $("seed").value = run.seed ?? 42;

  if (judge.provider && $("judgeProvider").querySelector(`option[value="${CSS.escape(judge.provider)}"]`)) {
    $("judgeProvider").value = judge.provider;
  }
  $("judgeModel").value = judge.model || JUDGE_DEFAULTS[$("judgeProvider").value];
  $("judgeMaxCases").value = judge.max_cases ?? 8;
  $("enableDeepEval").checked = Boolean(judge.enable_deepeval);
  $("enableRagas").checked = Boolean(judge.enable_ragas);

  applyProviderDefaults({ force: false });
  updateJudgeUI();
}

function numberInRange(id, min, max) {
  const element = $(id);
  const value = Number(element.value);
  if (!Number.isFinite(value) || value < min || value > max) {
    element.focus();
    throw new Error(`${element.previousElementSibling?.textContent || id} must be between ${min} and ${max}.`);
  }
  return value;
}

function buildPayload() {
  const targetModel = $("targetModel").value.trim();
  if (!targetModel) {
    $("targetModel").focus();
    throw new Error("Enter a target model name.");
  }

  const judgeEnabled = $("enableDeepEval").checked || $("enableRagas").checked;
  const judgeModel = $("judgeModel").value.trim();
  if (judgeEnabled && !judgeModel) {
    $("judgeModel").focus();
    throw new Error("Enter a judge model name.");
  }
  if (!state.enabledMetrics.length) {
    throw new Error("Select at least one metric on the Metric selection page.");
  }

  return {
    target_provider: $("targetProvider").value,
    target_model: targetModel,
    target_base_url: $("targetBaseUrl").value.trim() || "http://localhost:11434",
    max_records: numberInRange("maxRecords", 1, 100),
    repeat_count: numberInRange("repeatCount", 1, 10),
    seed: Number($("seed").value) || 42,
    enable_deepeval: $("enableDeepEval").checked,
    enable_ragas: $("enableRagas").checked,
    judge_provider: $("judgeProvider").value,
    judge_model: judgeModel || JUDGE_DEFAULTS[$("judgeProvider").value],
    judge_max_cases: numberInRange("judgeMaxCases", 1, 100),
    enabled_metrics: [...state.enabledMetrics],
  };
}

async function startRun() {
  if (state.activeRun) return;

  let payload;
  try {
    payload = buildPayload();
  } catch (error) {
    toast(error.message, "error", "Check configuration");
    return;
  }

  setRunButton(true);
  $("progressPanel").classList.remove("hidden");
  $("results").classList.add("hidden");
  $("progressMessage").textContent = "Submitting evaluation";
  $("progressPercent").textContent = "0%";
  $("progressBar").style.width = "0%";

  try {
    const started = await api("/api/run", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    state.activeRun = started.run_id;
    toast(`Run ${started.run_id} has started.`, "info", "Evaluation queued");
    await pollRun();
  } catch (error) {
    state.activeRun = null;
    setRunButton(false);
    toast(error.message, "error");
  }
}

async function pollRun() {
  if (!state.activeRun) return;

  try {
    const job = await api(`/api/run/${encodeURIComponent(state.activeRun)}`);
    const progress = Math.max(0, Math.min(100, Number(job.progress || 0)));
    $("progressMessage").textContent = job.message || job.stage || "Running";
    $("progressPercent").textContent = `${Math.round(progress)}%`;
    $("progressBar").style.width = `${progress}%`;

    if (job.status === "complete") {
      const completedRun = state.activeRun;
      state.activeRun = null;
      setRunButton(false);
      renderReport(job.report);
      await loadRuns();
      toast(`Run ${completedRun} completed with verdict ${job.report?.gate?.verdict || "unknown"}.`, "info", "Evaluation complete");
      return;
    }

    if (job.status === "failed") {
      const message = job.error || job.message || "Evaluation failed.";
      state.activeRun = null;
      setRunButton(false);
      toast(message, "error", "Run failed");
      return;
    }

    state.pollTimer = window.setTimeout(pollRun, 900);
  } catch (error) {
    state.activeRun = null;
    setRunButton(false);
    toast(error.message, "error", "Polling stopped");
  }
}

function renderMetricRows(aggregates = {}) {
  const entries = Object.entries(aggregates).sort(([a], [b]) => a.localeCompare(b));
  if (!entries.length) {
    return '<tr><td class="empty-state" colspan="5">No aggregate metrics were returned.</td></tr>';
  }

  return entries.map(([name, data]) => {
    const mean = Number(data.mean);
    const meanWidth = Number.isFinite(mean) ? Math.max(0, Math.min(100, mean * 100)) : 0;
    return `
      <tr>
        <td class="metric-cell">${escapeHTML(name)}</td>
        <td>
          <div class="metric-value">
            <span>${escapeHTML(fmt(data.mean))}</span>
            <span class="mini-bar" aria-hidden="true"><span style="width:${meanWidth}%"></span></span>
          </div>
        </td>
        <td>${escapeHTML(fmtPercent(data.pass_rate))}</td>
        <td>${escapeHTML(data.count ?? 0)}</td>
        <td class="${Number(data.error_count || 0) > 0 ? "error-text" : ""}">${escapeHTML(data.error_count ?? 0)}</td>
      </tr>`;
  }).join("");
}

function renderOwasp(items = []) {
  if (!items.length) {
    return '<div class="empty-state">No OWASP evidence mapping was returned.</div>';
  }

  return items.map((item) => `
    <article class="owasp-card ${safeClass(item.status)}">
      <strong>${escapeHTML(item.id)}</strong>
      <span>${escapeHTML(item.name)}</span>
      <em>${escapeHTML(String(item.status || "unknown").replaceAll("_", " "))}</em>
      <small>${escapeHTML(item.reason)}</small>
    </article>`).join("");
}

function renderStatusBox(targetId, data, trailingLabel) {
  const status = data?.status || "not_run";
  $(targetId).innerHTML = `
    <span class="tag ${safeClass(status)}">${escapeHTML(String(status).replaceAll("_", " "))}</span>
    <p>${escapeHTML(data?.reason || "No result available.")}</p>
    <small>${escapeHTML(trailingLabel)}</small>`;
}

function renderReport(report, { scroll = true } = {}) {
  if (!report) {
    toast("The server returned no report data.", "error");
    return;
  }

  $("results").classList.remove("hidden");
  $("progressPanel").classList.add("hidden");

  const verdict = report.gate?.verdict || "UNKNOWN";
  $("verdict").textContent = verdict;
  $("gateReason").textContent = (report.gate?.reasons || []).join("; ") || "No gate reason returned.";
  $("caseCount").textContent = report.summary?.case_count ?? "—";
  $("metricCount").textContent = report.summary?.metric_count ?? "—";
  $("criticalFailures").textContent = report.gate?.critical_failure_count ?? "—";

  const verdictCard = document.querySelector(".verdict-card");
  verdictCard.classList.toggle("pass", verdict === "PASS");
  verdictCard.classList.toggle("fail", verdict === "FAIL");

  const targetModel = report.manifest?.target_model || "unknown target";
  const createdAt = report.created_at ? fmtDate(report.created_at) : "unknown time";
  $("resultRunMeta").textContent = `${report.run_id} · ${targetModel} · ${createdAt}`;
  $("htmlReportLink").href = `/reports/${encodeURIComponent(report.run_id)}/report.html`;

  $("metricTable").innerHTML = renderMetricRows(report.aggregates || {});
  $("owaspGrid").innerHTML = renderOwasp(report.owasp || []);

  const regression = report.regression || {};
  renderStatusBox(
    "regressionBox",
    regression,
    `${(regression.comparisons || []).length} comparable metrics`,
  );

  const calibration = report.judge_calibration || {};
  renderStatusBox(
    "calibrationBox",
    calibration,
    `Weighted kappa: ${fmt(calibration.weighted_kappa)}`,
  );

  const failures = report.failures || [];
  $("failureCountLabel").textContent = `${failures.length} failure${failures.length === 1 ? "" : "s"}`;
  $("failureTable").innerHTML = failures.length
    ? failures.slice(0, 100).map((item) => `
      <tr>
        <td>${escapeHTML(item.case_id)}</td>
        <td>${escapeHTML(item.metric)}</td>
        <td>${escapeHTML(item.evaluator)}</td>
        <td>
          ${escapeHTML(item.reason)}
          ${item.error ? `<br><small class="error-text">${escapeHTML(item.error)}</small>` : ""}
        </td>
      </tr>`).join("")
    : '<tr><td class="empty-state" colspan="4">No failed checks.</td></tr>';

  if (scroll) {
    $("results").scrollIntoView({ behavior: "smooth", block: "start" });
  }
}

async function loadRuns() {
  try {
    const data = await api("/api/runs");
    state.baselineRunId = data.baseline_run_id || null;

    $("baselineBanner").classList.toggle("hidden", !state.baselineRunId);
    $("baselineRunId").textContent = state.baselineRunId || "—";

    const runs = data.runs || [];
    $("runsTable").innerHTML = runs.length
      ? runs.map((run) => {
        const isBaseline = run.run_id === state.baselineRunId;
        return `
          <tr>
            <td><span class="run-id" title="${escapeHTML(run.run_id)}">${escapeHTML(run.run_id)}</span></td>
            <td>${escapeHTML(fmtDate(run.created_at))}</td>
            <td>${escapeHTML(run.target || "—")}</td>
            <td>${escapeHTML(run.case_count ?? "—")}</td>
            <td><span class="tag ${safeClass(run.verdict)}">${escapeHTML(run.verdict || "—")}</span></td>
            <td>
              <div class="run-actions">
                <button class="table-button" type="button" data-action="dashboard" data-run-id="${escapeHTML(run.run_id)}">Dashboard</button>
                <a class="table-link" target="_blank" rel="noopener" href="/reports/${encodeURIComponent(run.run_id)}/report.html">Report</a>
                <button class="table-button ${isBaseline ? "baseline-active" : ""}" type="button" data-action="baseline" data-run-id="${escapeHTML(run.run_id)}" ${isBaseline ? "disabled" : ""}>${isBaseline ? "Baseline" : "Set baseline"}</button>
              </div>
            </td>
          </tr>`;
      }).join("")
      : '<tr><td class="empty-state" colspan="6">No completed runs yet.</td></tr>';
  } catch (error) {
    $("runsTable").innerHTML = `<tr><td class="empty-state error-text" colspan="6">${escapeHTML(error.message)}</td></tr>`;
    toast(error.message, "error", "Could not load runs");
  }
}

async function loadRunIntoDashboard(runId) {
  try {
    const job = await api(`/api/run/${encodeURIComponent(runId)}`);
    if (job.status !== "complete" || !job.report) {
      throw new Error("That run is not complete or its report is unavailable.");
    }
    renderReport(job.report);
  } catch (error) {
    toast(error.message, "error", "Could not open run");
  }
}

async function setBaseline(runId) {
  try {
    await api("/api/baseline", {
      method: "POST",
      body: JSON.stringify({ run_id: runId }),
    });
    toast(`Baseline set to ${runId}.`, "info", "Baseline updated");
    await loadRuns();
  } catch (error) {
    toast(error.message, "error", "Baseline update failed");
  }
}

function bindEvents() {
  $("runButton").addEventListener("click", startRun);
  $("refreshRuns").addEventListener("click", loadRuns);

  $("targetProvider").addEventListener("change", () => applyProviderDefaults({ force: true }));
  $("targetModel").addEventListener("input", updateHeroSummary);
  $("judgeProvider").addEventListener("change", () => applyJudgeDefaults({ force: true }));
  $("judgeModel").addEventListener("input", updateHeroSummary);
  $("enableDeepEval").addEventListener("change", updateJudgeUI);
  $("enableRagas").addEventListener("change", updateJudgeUI);

  $("runsTable").addEventListener("click", (event) => {
    const control = event.target.closest("[data-action][data-run-id]");
    if (!control) return;
    const runId = control.dataset.runId;
    if (control.dataset.action === "baseline") setBaseline(runId);
    if (control.dataset.action === "dashboard") loadRunIntoDashboard(runId);
  });

  window.addEventListener("beforeunload", () => {
    if (state.pollTimer) window.clearTimeout(state.pollTimer);
  });
}

async function init() {
  bindEvents();
  updateJudgeUI();

  const results = await Promise.allSettled([loadConfig(), loadMetricSelection(), loadRuns()]);
  results.forEach((result) => {
    if (result.status === "rejected") {
      toast(result.reason?.message || "Initialization failed.", "error", "Dashboard startup issue");
    }
  });
}

init();
