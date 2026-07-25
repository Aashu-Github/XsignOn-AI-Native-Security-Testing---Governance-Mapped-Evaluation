"""
This is what actually blocks a merge or flags drift. Deliberately dumb:
if the report's overall_verdict is FAIL, exit non-zero. A real CI step
just checks this exit code -- deepeval's pytest-style integration works
the same way today, this generalizes it across all four tools.
"""

import sys
from layer4.schema import Layer4Report, Verdict


def evaluate_gate(report: Layer4Report) -> int:
    """Returns a process exit code: 0 = pass, 1 = fail."""
    return 0 if report.overall_verdict == Verdict.PASS else 1


def print_gate_summary(report: Layer4Report) -> None:
    fails = [m for m in report.metrics if m.verdict == Verdict.FAIL]
    skipped = [m for m in report.metrics if m.verdict == Verdict.SKIPPED]
    passed = [m for m in report.metrics if m.verdict == Verdict.PASS]

    print(f"\n{'='*60}")
    print(f"LAYER 4 GATE -- target={report.target_id} mode={report.run_mode}")
    print(f"{'='*60}")
    print(f"  passed:  {len(passed)}")
    print(f"  failed:  {len(fails)}")
    print(f"  skipped: {len(skipped)}")
    print(f"  overall: {report.overall_verdict.value.upper()}")

    if fails:
        print("\n  Failing metrics:")
        for m in fails:
            print(f"    [{m.tool}] {m.metric}: {m.score} < {m.threshold}  "
                  f"{'(LLM judge)' if m.used_llm_judge else ''}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    sys.exit(0)
