"use strict";

const METRIC_STORAGE_KEY = "xsignon-layer4-enabled-metrics-v1";
const $ = (id) => document.getElementById(id);

const state = {
  catalog: [],
  defaults: [],
  enabled: new Set(),
  draggedMetricId: null,
};

function escapeHTML(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function toast(message, type = "info") {
  const region = $("toastRegion");
  const item = document.createElement("div");
  item.className = `toast ${type}`;
  item.innerHTML = `<div><strong>Metric selection</strong><p>${escapeHTML(message)}</p></div><button type="button" aria-label="Dismiss notification">×</button>`;
  item.querySelector("button").addEventListener("click", () => item.remove());
  region.appendChild(item);
  window.setTimeout(() => item.remove(), 4000);
}

async function api(path) {
  const response = await fetch(path, { cache: "no-store" });
  const body = await response.json();
  if (!response.ok) throw new Error(body.error || `Request failed: ${response.status}`);
  return body;
}

function readStored(defaults) {
  try {
    const parsed = JSON.parse(localStorage.getItem(METRIC_STORAGE_KEY) || "null");
    if (Array.isArray(parsed)) return parsed.map(String);
  } catch (_) {
    // Ignore invalid browser storage.
  }
  return [...defaults];
}

function saveSelection() {
  const ordered = state.catalog.filter((metric) => state.enabled.has(metric.id)).map((metric) => metric.id);
  localStorage.setItem(METRIC_STORAGE_KEY, JSON.stringify(ordered));
  $("metricSaveStatus").lastElementChild.textContent = "Saved in this browser";
}

function moveMetric(metricId, destination) {
  if (destination === "tested") state.enabled.add(metricId);
  else state.enabled.delete(metricId);
  saveSelection();
  render();
}

function metricCard(metric, isEnabled) {
  const requirement = metric.requires
    ? `<span class="metric-requirement">Requires ${escapeHTML(metric.requires)}</span>`
    : "";
  const destination = isEnabled ? "not-tested" : "tested";
  const action = isEnabled ? "Move to Not tested" : "Move to Tested";
  return `
    <article class="metric-drag-card" draggable="true" data-metric-id="${escapeHTML(metric.id)}">
      <div class="metric-drag-handle" aria-hidden="true">⠿</div>
      <div class="metric-drag-content">
        <div class="metric-card-topline">
          <span class="metric-group">${escapeHTML(metric.group)}</span>
          ${requirement}
        </div>
        <h3>${escapeHTML(metric.label)}</h3>
        <code>${escapeHTML(metric.id)}</code>
        <p>${escapeHTML(metric.description)}</p>
      </div>
      <button class="metric-move-button" type="button" data-move-to="${destination}" aria-label="${escapeHTML(action)}: ${escapeHTML(metric.label)}">${escapeHTML(action)}</button>
    </article>`;
}

function render() {
  const tested = state.catalog.filter((metric) => state.enabled.has(metric.id));
  const notTested = state.catalog.filter((metric) => !state.enabled.has(metric.id));

  $("testedMetrics").innerHTML = tested.length
    ? tested.map((metric) => metricCard(metric, true)).join("")
    : '<div class="metric-empty">Drop metrics here to test them.</div>';
  $("notTestedMetrics").innerHTML = notTested.length
    ? notTested.map((metric) => metricCard(metric, false)).join("")
    : '<div class="metric-empty">All selectable metrics are currently tested.</div>';

  $("testedCount").textContent = tested.length;
  $("notTestedCount").textContent = notTested.length;
  $("metricSelectionCount").textContent = `${tested.length} of ${state.catalog.length} metrics will be tested`;

  bindCards();
}

function bindCards() {
  document.querySelectorAll(".metric-drag-card").forEach((card) => {
    card.addEventListener("dragstart", (event) => {
      state.draggedMetricId = card.dataset.metricId;
      card.classList.add("is-dragging");
      event.dataTransfer.effectAllowed = "move";
      event.dataTransfer.setData("text/plain", state.draggedMetricId);
    });
    card.addEventListener("dragend", () => {
      state.draggedMetricId = null;
      card.classList.remove("is-dragging");
      document.querySelectorAll(".metric-zone").forEach((zone) => zone.classList.remove("drag-over"));
    });
  });

  document.querySelectorAll(".metric-move-button").forEach((button) => {
    button.addEventListener("click", () => {
      const card = button.closest(".metric-drag-card");
      moveMetric(card.dataset.metricId, button.dataset.moveTo);
    });
  });
}

function bindDropZones() {
  document.querySelectorAll(".metric-zone").forEach((zone) => {
    zone.addEventListener("dragover", (event) => {
      event.preventDefault();
      event.dataTransfer.dropEffect = "move";
      zone.classList.add("drag-over");
    });
    zone.addEventListener("dragleave", (event) => {
      if (!zone.contains(event.relatedTarget)) zone.classList.remove("drag-over");
    });
    zone.addEventListener("drop", (event) => {
      event.preventDefault();
      zone.classList.remove("drag-over");
      const metricId = event.dataTransfer.getData("text/plain") || state.draggedMetricId;
      if (metricId) moveMetric(metricId, zone.dataset.zone);
    });
  });
}

async function init() {
  bindDropZones();
  $("testAllMetrics").addEventListener("click", () => {
    state.enabled = new Set(state.catalog.map((metric) => metric.id));
    saveSelection();
    render();
    toast("All selectable metrics will be tested.");
  });
  $("resetMetrics").addEventListener("click", () => {
    state.enabled = new Set(state.defaults);
    saveSelection();
    render();
    toast("Metric selection reset to project defaults.");
  });

  try {
    const data = await api("/api/metrics");
    state.catalog = data.catalog || [];
    state.defaults = data.default_enabled || state.catalog.map((metric) => metric.id);
    const valid = new Set(state.catalog.map((metric) => metric.id));
    state.enabled = new Set(readStored(state.defaults).filter((id) => valid.has(id)));
    if (!state.enabled.size) state.enabled = new Set(state.defaults);
    saveSelection();
    render();
  } catch (error) {
    $("metricSaveStatus").lastElementChild.textContent = "Could not load metrics";
    toast(error.message, "error");
  }
}

init();
