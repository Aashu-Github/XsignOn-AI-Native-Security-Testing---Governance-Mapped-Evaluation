"""XSignOn L2 ingestion runner — select which tools to run."""
import argparse
import db
import garak_adapter
import pyrit_adapter
import promptfoo_adapter

ADAPTERS = {
    "garak": garak_adapter.ingest,
    "pyrit": pyrit_adapter.ingest,
    "promptfoo": promptfoo_adapter.ingest,
}


def run(tools=None, clear=False, target_model="llama3.2:3b"):
    """Run selected adapters. tools=None runs all."""
    db.init_db()

    selected = tools or list(ADAPTERS.keys())
    unknown = [t for t in selected if t not in ADAPTERS]
    if unknown:
        raise ValueError(f"Unknown tool(s): {unknown}. Available: {list(ADAPTERS)}")

    if clear:
        for tool in selected:
            db.clear_findings(source_tool=tool)
            print(f"[runner] cleared existing {tool} findings")

    total = 0
    for tool in selected:
        try:
            if tool == "promptfoo":
                total += ADAPTERS[tool]()
            else:
                total += ADAPTERS[tool](target_model=target_model)
        except Exception as e:
            print(f"[runner] {tool} adapter failed: {e}")

    print(f"\n[runner] total inserted: {total}")
    print(f"[runner] findings by tool: {db.count_by_tool()}")
    return total


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="XSignOn Layer 2 ingestion")
    ap.add_argument("--tools", nargs="+", choices=list(ADAPTERS),
                    help="which tools to ingest (default: all)")
    ap.add_argument("--clear", action="store_true",
                    help="clear existing findings for selected tools first")
    ap.add_argument("--model", default="llama3.2:3b", help="target model label")
    args = ap.parse_args()
    run(tools=args.tools, clear=args.clear, target_model=args.model)