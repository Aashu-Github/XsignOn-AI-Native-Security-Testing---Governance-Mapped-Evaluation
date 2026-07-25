"""
Writes both output shapes mentioned in the doc: JSON (what Layer 5 would
ingest) and HTML (what a human looks at, same idea as deepeval's own
HTML output today, just generalized across all four tools now that
they're normalized into one schema).
"""

import json
from pathlib import Path
from layer4.schema import Layer4Report


def write_json(report: Layer4Report, path: str) -> None:
    Path(path).write_text(json.dumps(report.to_dict(), indent=2))


def write_html(report: Layer4Report, path: str) -> None:
    rows = ""
    for m in report.metrics:
        color = {"pass": "#1a7f37", "fail": "#cf222e", "skipped": "#6e7781"}[m.verdict.value]
        score_str = "--" if m.score is None else f"{m.score:.3f}"
        thresh_str = "--" if m.threshold is None else f"{m.threshold:.2f}"
        judge = "🧑‍⚖️" if m.used_llm_judge else ""
        owasp = ", ".join(m.owasp_mapping) if m.owasp_mapping else "--"
        rows += f"""
        <tr>
          <td>{m.tool}</td>
          <td>{m.metric}</td>
          <td>{score_str}</td>
          <td>{thresh_str}</td>
          <td style="color:{color};font-weight:600">{m.verdict.value.upper()} {judge}</td>
          <td>{owasp}</td>
          <td style="color:#6e7781;font-size:0.85em">{m.notes}</td>
        </tr>"""

    overall = report.overall_verdict.value.upper()
    overall_color = "#1a7f37" if overall == "PASS" else "#cf222e"

    html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>Layer 4 Report -- {report.target_id}</title>
<style>
  body {{ font-family: -apple-system, Helvetica, Arial, sans-serif; margin: 2rem; color: #1f2328; }}
  h1 {{ font-size: 1.4rem; }}
  table {{ border-collapse: collapse; width: 100%; margin-top: 1rem; }}
  th, td {{ border: 1px solid #d0d7de; padding: 6px 10px; text-align: left; font-size: 0.9rem; }}
  th {{ background: #f6f8fa; }}
  .badge {{ display: inline-block; padding: 4px 12px; border-radius: 6px; color: white;
            background: {overall_color}; font-weight: 700; }}
  .meta {{ color: #57606a; font-size: 0.85rem; }}
</style></head>
<body>
  <h1>Layer 4 Evaluation Report</h1>
  <p><b>Target:</b> {report.target_id} ({report.target_type}) &nbsp;|&nbsp;
     <b>Mode:</b> {report.run_mode} &nbsp;|&nbsp;
     <span class="badge">{overall}</span></p>
  <p class="meta">Started: {report.started_at}<br>Finished: {report.finished_at}</p>
  <table>
    <tr><th>Tool</th><th>Metric</th><th>Score</th><th>Threshold</th><th>Verdict</th><th>OWASP/ATLAS</th><th>Notes</th></tr>
    {rows}
  </table>
</body></html>"""
    Path(path).write_text(html)
