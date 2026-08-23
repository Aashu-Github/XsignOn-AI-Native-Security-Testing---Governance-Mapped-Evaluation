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
    summary = report.get("summary", {})
    run_id = html.escape(str(report.get("run_id", "")))
    target = html.escape(str(report.get("manifest", {}).get("target_model", "unknown")))

    aggregate_rows = "".join(
        f"<tr><td class='mono'>{html.escape(name)}</td><td>{_fmt(data.get('mean'))}</td><td>{_fmt(data.get('pass_rate'))}</td><td>{data.get('count', 0)}</td></tr>"
        for name, data in sorted(aggregates.items())
    ) or "<tr><td colspan='4' class='empty'>No aggregate metrics returned.</td></tr>"

    owasp_cards = "".join(
        f"<article class='owasp {html.escape(str(item.get('status', 'unknown')))}'><strong>{html.escape(str(item.get('id', '')))}</strong><span>{html.escape(str(item.get('name', '')))}</span><em>{html.escape(str(item.get('status', 'unknown')).replace('_', ' '))}</em><small>{html.escape(str(item.get('reason', '')))}</small></article>"
        for item in owasp
    ) or "<div class='empty'>No OWASP evidence returned.</div>"

    failure_rows = "".join(
        f"<tr><td class='mono'>{html.escape(str(item.get('case_id')))}</td><td>{html.escape(str(item.get('metric')))}</td><td>{html.escape(str(item.get('reason')))}</td><td class='error'>{html.escape(str(item.get('error') or ''))}</td></tr>"
        for item in failures[:200]
    ) or "<tr><td colspan='4' class='empty'>No failed checks.</td></tr>"

    raw = html.escape(json.dumps(report.get("manifest", {}), indent=2))
    verdict_class = "pass" if verdict == "PASS" else "fail" if verdict == "FAIL" else "unknown"

    return f"""<!doctype html>
<html lang='en'>
<head>
<meta charset='utf-8'>
<meta name='viewport' content='width=device-width,initial-scale=1'>
<meta name='theme-color' content='#0a0e14'>
<title>XSignOn — Layer 4 Report</title>
<style>
:root{{--bg:#0a0e14;--bg2:#0e131c;--panel:#121826;--panel2:#161d2c;--panel3:#1b2437;--border:#232d40;--border2:#2e3a52;--text:#e7edf6;--muted:#8a97ad;--dim:#5d6a80;--blue:#3d8bff;--cyan:#2dd4bf;--purple:#a371f7;--green:#3fb950;--amber:#e3b341;--red:#f76d6d;--mono:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;--sans:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Arial,sans-serif}}
*{{box-sizing:border-box;margin:0;padding:0}} body{{font:14px/1.45 var(--sans);background:var(--bg);color:var(--text)}}
.topbar{{height:52px;background:var(--bg2);border-bottom:1px solid var(--border);display:flex;align-items:center;padding:0 16px;gap:10px;position:sticky;top:0;z-index:10}} .mark{{width:28px;height:28px;border-radius:7px;background:linear-gradient(135deg,var(--blue),var(--purple));display:grid;place-items:center;font:800 12px var(--mono)}} .brand{{font-weight:750}} .brand small{{display:block;color:var(--dim);font-size:9px;letter-spacing:1px}} .status{{margin-left:auto;color:var(--muted);font-size:12px;background:var(--panel);border:1px solid var(--border);border-radius:7px;padding:5px 9px}}
.shell{{display:grid;grid-template-columns:220px minmax(0,1fr);min-height:calc(100vh - 52px)}} aside{{background:var(--bg2);border-right:1px solid var(--border);padding:14px 10px}} .nav-title{{color:var(--dim);font-size:10px;text-transform:uppercase;letter-spacing:1px;padding:10px}} .nav-item{{padding:9px 10px;border-radius:7px;color:var(--muted);font-size:13px}} .nav-item.active{{background:var(--panel2);color:var(--text);border-left:3px solid var(--blue)}} .layer-stack{{display:flex;gap:6px;padding:6px 10px}} .layer{{padding:4px 7px;border-radius:6px;background:var(--panel3);border:1px solid var(--border2);font:11px var(--mono);color:var(--dim)}} .layer.active{{color:var(--cyan);border-color:rgba(45,212,191,.55)}}
main{{padding:20px 24px 44px;min-width:0}} .crumb{{color:var(--dim);font-size:11px;margin-bottom:5px}} h1{{font-size:20px;margin-bottom:5px}} .sub{{color:var(--muted);font-size:12px}} .stats{{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px;margin:16px 0}} .stat,.panel{{background:var(--panel);border:1px solid var(--border);border-radius:10px;padding:14px}} .stat .k{{color:var(--muted);font-size:10px;text-transform:uppercase;letter-spacing:.5px}} .stat .v{{font-size:25px;font-weight:800;margin-top:6px}} .stat.pass{{border-color:rgba(63,185,80,.6)}} .stat.pass .v{{color:var(--green)}} .stat.fail{{border-color:rgba(247,109,109,.6)}} .stat.fail .v{{color:var(--red)}}
.panel{{margin-bottom:16px;padding:16px}} .panel h2{{font-size:13px;margin-bottom:12px}} .panel-note{{color:var(--dim);font-size:11px;margin-top:-8px;margin-bottom:12px}} .table-wrap{{overflow-x:auto}} table{{width:100%;border-collapse:collapse}} th{{text-align:left;color:var(--dim);font-size:10px;text-transform:uppercase;letter-spacing:.5px;padding:8px 10px;border-bottom:1px solid var(--border)}} td{{padding:10px;border-bottom:1px solid var(--border);font-size:12px;vertical-align:top}} .mono{{font-family:var(--mono);font-size:11px}} .error{{color:var(--red)}} .empty{{color:var(--dim);text-align:center;padding:18px}}
.grid{{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:9px}} .owasp{{background:var(--panel2);border:1px solid var(--border);border-radius:8px;padding:10px;min-height:105px}} .owasp strong{{display:block;font:700 11px var(--mono);color:var(--cyan)}} .owasp span{{display:block;font-size:11.5px;margin:4px 0}} .owasp em{{font-style:normal;font-size:9.5px;text-transform:uppercase;color:var(--muted);background:var(--panel3);border-radius:12px;padding:2px 6px}} .owasp small{{display:block;color:var(--dim);font-size:10px;margin-top:6px}} .owasp.pass{{border-color:rgba(63,185,80,.4)}} .owasp.fail{{border-color:rgba(247,109,109,.4)}} .owasp.manual_review{{border-color:rgba(227,179,65,.4)}} pre{{white-space:pre-wrap;word-break:break-word;background:var(--panel2);border:1px solid var(--border);border-radius:8px;padding:12px;color:var(--muted);font:11px/1.5 var(--mono)}}
@media(max-width:950px){{.shell{{display:block}} aside{{display:none}} .stats,.grid{{grid-template-columns:repeat(2,1fr)}}}} @media(max-width:620px){{main{{padding:16px}} .stats,.grid{{grid-template-columns:1fr}}}}
</style>
</head>
<body>
<header class='topbar'><div class='mark'>X4</div><div class='brand'>XSignOn<small>AI SECURITY · LAYER 4 REPORT</small></div><div class='status'>Run {run_id}</div></header>
<div class='shell'>
<aside><div class='nav-title'>Report</div><div class='nav-item active'>◎ Evaluation results</div><div class='nav-title'>Layer stack</div><div class='layer-stack'><span class='layer'>L2</span><span class='layer'>L3</span><span class='layer active'>L4</span><span class='layer'>L5</span><span class='layer'>L6</span></div></aside>
<main>
<div class='crumb'>XSignOn / Layer 4 / Report</div><h1>Evaluation Report</h1><p class='sub'>{run_id} · target {target}</p>
<div class='stats'>
<article class='stat {verdict_class}'><div class='k'>Gate verdict</div><div class='v'>{html.escape(verdict)}</div></article>
<article class='stat'><div class='k'>Cases</div><div class='v'>{summary.get('case_count', 0)}</div></article>
<article class='stat'><div class='k'>Traces</div><div class='v'>{summary.get('trace_count', 0)}</div></article>
<article class='stat'><div class='k'>Failed checks</div><div class='v'>{len(failures)}</div></article>
</div>
<section class='panel'><h2>Metric aggregates</h2><p class='panel-note'>Measured scores and pass rates for this run.</p><div class='table-wrap'><table><thead><tr><th>Metric</th><th>Mean</th><th>Pass rate</th><th>Count</th></tr></thead><tbody>{aggregate_rows}</tbody></table></div></section>
<section class='panel'><h2>OWASP GenAI / LLM Top 10 evidence</h2><p class='panel-note'>Evidence mapping from this evaluation; not a certification.</p><div class='grid'>{owasp_cards}</div></section>
<section class='panel'><h2>Failed checks</h2><p class='panel-note'>Checks that did not meet the configured gate.</p><div class='table-wrap'><table><thead><tr><th>Case</th><th>Metric</th><th>Reason</th><th>Error</th></tr></thead><tbody>{failure_rows}</tbody></table></div></section>
<section class='panel'><h2>Run manifest</h2><p class='panel-note'>Target, judge, dataset, environment, and traceability metadata.</p><pre>{raw}</pre></section>
</main></div></body></html>"""
