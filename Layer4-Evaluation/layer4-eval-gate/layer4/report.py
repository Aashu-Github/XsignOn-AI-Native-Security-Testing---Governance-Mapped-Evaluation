"""Renders a static HTML report from a real GateRun — same visual shape as
the interactive demo (bars per OWASP category, conditional RAGAS block,
pass/fail verdict banner), but every number comes from an actual gate run
instead of a hardcoded DATA object.
"""

from __future__ import annotations

from pathlib import Path

from layer4.schema import GateRun

_ROW_TEMPLATE = """
<div class="row">
  <div class="row-label">
    <p class="row-name">{label}</p>
    <p class="row-sub">{category}</p>
  </div>
  <div class="row-track">
    <div class="row-fill {fill_class}" style="width:{pct}%;"></div>
  </div>
  <div class="row-score">{score:.2f}</div>
  <div class="row-badge {badge_class}">{badge_text}</div>
</div>
"""

_PAGE_TEMPLATE = """<!doctype html>
<html>
<head>
<meta charset="utf-8">
<title>Layer 4 gate report — {target_name}</title>
<style>
  body {{ font-family: -apple-system, Helvetica, Arial, sans-serif; background:#0b0d10; color:#e6e6e6; margin:0; padding:32px; }}
  .card {{ max-width:820px; margin:0 auto; }}
  h1 {{ font-size:20px; font-weight:600; margin-bottom:4px; }}
  .meta {{ color:#9aa0a6; font-size:13px; margin-bottom:24px; }}
  .verdict {{ border-radius:12px; padding:16px 20px; margin-bottom:24px; display:flex; justify-content:space-between; align-items:center; }}
  .verdict.block {{ background:#3a1414; }}
  .verdict.allow {{ background:#12321a; }}
  .verdict-text {{ font-size:18px; font-weight:600; }}
  .verdict.block .verdict-text {{ color:#ff8080; }}
  .verdict.allow .verdict-text {{ color:#7be08a; }}
  .section-title {{ font-size:13px; color:#9aa0a6; margin:20px 0 8px; text-transform:uppercase; letter-spacing:.04em; }}
  .row {{ display:flex; align-items:center; gap:12px; padding:8px 0; border-bottom:1px solid #1f2328; }}
  .row-label {{ width:220px; flex-shrink:0; }}
  .row-name {{ font-size:13px; font-weight:500; margin:0; }}
  .row-sub {{ font-size:12px; color:#9aa0a6; margin:0; }}
  .row-track {{ flex:1; height:8px; background:#1a1d21; border-radius:4px; overflow:hidden; }}
  .row-fill {{ height:100%; border-radius:4px; }}
  .row-fill.pass {{ background:#639922; }}
  .row-fill.fail {{ background:#E24B4A; }}
  .row-score {{ width:48px; text-align:right; font-size:13px; font-weight:500; }}
  .row-badge {{ width:52px; text-align:center; font-size:12px; padding:2px 8px; border-radius:6px; }}
  .row-badge.pass {{ background:#12321a; color:#7be08a; }}
  .row-badge.fail {{ background:#3a1414; color:#ff8080; }}
</style>
</head>
<body>
<div class="card">
  <h1>Layer 4 gate report</h1>
  <p class="meta">target: {target_name} ({target_type}) &middot; run at {timestamp}</p>
  <div class="verdict {verdict_class}">
    <div>
      <p class="meta" style="margin:0 0 2px;">CI gate verdict</p>
      <p class="verdict-text">{verdict_text}</p>
    </div>
    <div class="meta">{fail_count} metric(s) below threshold</div>
  </div>

  <p class="section-title">deepeval — OWASP LLM Top 10</p>
  {deepeval_rows}

  {ragas_section}
</div>
</body>
</html>
"""

_RAGAS_SECTION_TEMPLATE = """
<p class="section-title">RAGAS — activated (target type: rag)</p>
{ragas_rows}
"""


def _row_html(r) -> str:
    pct = max(0, min(100, round(r.score * 100)))
    return _ROW_TEMPLATE.format(
        label=r.label,
        category=r.category,
        pct=pct,
        score=r.score,
        fill_class="pass" if r.passed else "fail",
        badge_class="pass" if r.passed else "fail",
        badge_text="pass" if r.passed else "fail",
    )


def render_report(run: GateRun, output_path: str | Path) -> Path:
    deepeval_results = [r for r in run.results if r.tool == "deepeval"]
    ragas_results = [r for r in run.results if r.tool == "ragas"]

    deepeval_rows = "\n".join(_row_html(r) for r in deepeval_results)

    ragas_section = ""
    if ragas_results:
        ragas_rows = "\n".join(_row_html(r) for r in ragas_results)
        ragas_section = _RAGAS_SECTION_TEMPLATE.format(ragas_rows=ragas_rows)

    page = _PAGE_TEMPLATE.format(
        target_name=run.target_name,
        target_type=run.target_type,
        timestamp=run.timestamp,
        verdict_class="block" if run.blocked else "allow",
        verdict_text="Block merge" if run.blocked else "Allow merge",
        fail_count=len(run.failures),
        deepeval_rows=deepeval_rows,
        ragas_section=ragas_section,
    )

    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(page)
    return out
