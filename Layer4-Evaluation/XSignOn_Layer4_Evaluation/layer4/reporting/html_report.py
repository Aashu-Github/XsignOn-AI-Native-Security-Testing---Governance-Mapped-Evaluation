from __future__ import annotations

import html
import json
from typing import Any


def _fmt(value: Any) -> str:
    if value is None:
        return "—"
    if isinstance(value, float):
        return f"{value:.3f}"
    return html.escape(str(value))


def render_html_report(report: dict[str, Any]) -> str:
    verdict = report.get("gate", {}).get("verdict", "UNKNOWN")
    aggregates = report.get("aggregates", {})
    owasp = report.get("owasp", [])
    failures = report.get("failures", [])
    aggregate_rows = "".join(
        f"<tr><td>{html.escape(name)}</td><td>{_fmt(data.get('mean'))}</td><td>{_fmt(data.get('pass_rate'))}</td><td>{data.get('count', 0)}</td></tr>"
        for name, data in sorted(aggregates.items())
    )
    owasp_cards = "".join(
        f"<div class='owasp {item['status']}'><strong>{html.escape(item['id'])}</strong><span>{html.escape(item['name'])}</span><em>{html.escape(item['status'])}</em><small>{html.escape(item['reason'])}</small></div>"
        for item in owasp
    )
    failure_rows = "".join(
        f"<tr><td>{html.escape(str(item.get('case_id')))}</td><td>{html.escape(str(item.get('metric')))}</td><td>{html.escape(str(item.get('reason')))}</td><td>{html.escape(str(item.get('error') or ''))}</td></tr>"
        for item in failures[:200]
    ) or "<tr><td colspan='4'>No failed checks.</td></tr>"
    raw = html.escape(json.dumps(report.get("manifest", {}), indent=2))
    return f"""<!doctype html>
<html><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>
<title>XSignOn Layer 4 Report</title>
<style>
body{{font-family:Inter,Arial,sans-serif;background:#08111f;color:#e8eef8;margin:0;padding:32px}} .wrap{{max-width:1200px;margin:auto}}
h1,h2{{margin:0 0 18px}} .badge{{display:inline-block;padding:8px 14px;border-radius:999px;background:{'#1f8f55' if verdict=='PASS' else '#b63b3b'};font-weight:800}}
.card{{background:#111d2e;border:1px solid #26364f;border-radius:16px;padding:20px;margin:18px 0}} table{{width:100%;border-collapse:collapse}} th,td{{text-align:left;padding:10px;border-bottom:1px solid #26364f;vertical-align:top}}
.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(230px,1fr));gap:12px}} .owasp{{padding:14px;border-radius:12px;background:#17253a;border-left:5px solid #64748b;display:flex;flex-direction:column;gap:5px}} .owasp.pass{{border-color:#22c55e}} .owasp.fail{{border-color:#ef4444}} .owasp.manual_review{{border-color:#f59e0b}} .owasp.not_applicable{{border-color:#3b82f6}} small{{color:#b8c4d7}} pre{{white-space:pre-wrap;word-break:break-word}}
</style></head><body><div class='wrap'>
<h1>XSignOn Layer 4 Evaluation Report</h1><p><span class='badge'>{html.escape(verdict)}</span> Run {html.escape(report.get('run_id',''))}</p>
<div class='card'><h2>Summary</h2><p>Cases: {report.get('summary',{}).get('case_count',0)} · Traces: {report.get('summary',{}).get('trace_count',0)} · Failed checks: {len(failures)}</p></div>
<div class='card'><h2>Metric aggregates</h2><table><thead><tr><th>Metric</th><th>Mean</th><th>Pass rate</th><th>Count</th></tr></thead><tbody>{aggregate_rows}</tbody></table></div>
<div class='card'><h2>OWASP GenAI/LLM Top 10 2026</h2><div class='grid'>{owasp_cards}</div></div>
<div class='card'><h2>Failures</h2><table><thead><tr><th>Case</th><th>Metric</th><th>Reason</th><th>Error</th></tr></thead><tbody>{failure_rows}</tbody></table></div>
<div class='card'><h2>Run manifest</h2><pre>{raw}</pre></div>
</div></body></html>"""
