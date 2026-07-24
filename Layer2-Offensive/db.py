"""Shared database layer for XSignOn Layer 2."""
import hashlib
import sqlite3
import uuid

FINDINGS_DB = "findings.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS findings (
    finding_id           TEXT PRIMARY KEY,
    run_id               TEXT,
    source_tool          TEXT NOT NULL,
    attack               TEXT,
    target_model         TEXT,
    prompt               TEXT,
    response             TEXT,
    tool_flagged         INTEGER,
    tool_verdict_raw     TEXT,
    tool_rationale       TEXT,
    verified             INTEGER,
    verification_method  TEXT,
    confidence           REAL,
    status               TEXT,
    created_at           TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_findings_run   ON findings(run_id);
CREATE INDEX IF NOT EXISTS idx_findings_tool  ON findings(source_tool);
CREATE INDEX IF NOT EXISTS idx_findings_status ON findings(status);

-- Each layer records its OWN assessment here instead of overwriting L2's.
CREATE TABLE IF NOT EXISTS layer_verdicts (
    verdict_id    TEXT PRIMARY KEY,
    finding_id    TEXT NOT NULL,
    layer         TEXT NOT NULL,      -- 'L2' | 'L3' | 'L4' | 'L5'
    component     TEXT,               -- e.g. 'honest_scorer', 'llama_guard'
    verdict       INTEGER,            -- 1 = harm confirmed, 0 = no harm, NULL = unknown
    confidence    REAL,
    method        TEXT,
    rationale     TEXT,
    created_at    TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(finding_id) REFERENCES findings(finding_id)
);
CREATE INDEX IF NOT EXISTS idx_verdicts_finding ON layer_verdicts(finding_id);
CREATE INDEX IF NOT EXISTS idx_verdicts_layer   ON layer_verdicts(layer);
"""


def get_connection(db_path=FINDINGS_DB):
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    return conn


def init_db(db_path=FINDINGS_DB):
    conn = get_connection(db_path)
    conn.executescript(SCHEMA)
    conn.commit()
    conn.close()


def migrate(db_path=FINDINGS_DB):
    """Add new columns/tables to an existing database without losing data."""
    conn = get_connection(db_path)
    cols = {r[1] for r in conn.execute("PRAGMA table_info(findings)").fetchall()}
    for col, decl in [("run_id", "TEXT"), ("created_at", "TEXT")]:
        if col not in cols:
            conn.execute(f"ALTER TABLE findings ADD COLUMN {col} {decl}")
            print(f"[migrate] added findings.{col}")
    conn.executescript(SCHEMA)
    conn.commit()
    conn.close()
    print("[migrate] done")


def make_run_id(source_tool, artifact_key):
    """Stable run id derived from the source artifact, so re-ingesting is a no-op."""
    h = hashlib.sha256(f"{source_tool}|{artifact_key}".encode()).hexdigest()[:12]
    return f"{source_tool}-{h}"


def make_finding_id(run_id, source_tool, attack, prompt, response, discriminator=""):
    """Content-derived id → same finding always maps to the same row."""
    raw = "|".join([run_id or "", source_tool, attack or "", prompt or "",
                    (response or "")[:2000], str(discriminator)])
    return hashlib.sha256(raw.encode()).hexdigest()[:32]


def clear_findings(source_tool=None, run_id=None, db_path=FINDINGS_DB):
    conn = get_connection(db_path)
    if run_id:
        conn.execute("DELETE FROM layer_verdicts WHERE finding_id IN "
                     "(SELECT finding_id FROM findings WHERE run_id = ?)", [run_id])
        conn.execute("DELETE FROM findings WHERE run_id = ?", [run_id])
    elif source_tool:
        conn.execute("DELETE FROM layer_verdicts WHERE finding_id IN "
                     "(SELECT finding_id FROM findings WHERE source_tool = ?)", [source_tool])
        conn.execute("DELETE FROM findings WHERE source_tool = ?", [source_tool])
    else:
        conn.execute("DELETE FROM layer_verdicts")
        conn.execute("DELETE FROM findings")
    conn.commit()
    conn.close()


def insert_finding(source_tool, attack, target_model, prompt, response,
                   tool_flagged=None, tool_verdict_raw=None, tool_rationale=None,
                   run_id=None, discriminator="", conn=None, db_path=FINDINGS_DB):
    """Insert one finding. Duplicate-safe: re-inserting the same content is ignored.
    Returns (finding_id, inserted_bool)."""
    own = conn is None
    if own:
        conn = get_connection(db_path)

    finding_id = make_finding_id(run_id, source_tool, attack, prompt, response, discriminator)
    cur = conn.execute(
        """INSERT OR IGNORE INTO findings
           (finding_id, run_id, source_tool, attack, target_model,
            prompt, response, tool_flagged, tool_verdict_raw, tool_rationale)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        [finding_id, run_id, source_tool, attack, target_model,
         prompt, response, tool_flagged, tool_verdict_raw, tool_rationale])
    inserted = cur.rowcount > 0

    if own:
        conn.commit()
        conn.close()
    return finding_id, inserted


def record_layer_verdict(finding_id, layer, component, verdict, confidence,
                         method, rationale=None, conn=None, db_path=FINDINGS_DB):
    """Any layer (L2-L5) records its own assessment without overwriting others."""
    own = conn is None
    if own:
        conn = get_connection(db_path)
    vid = hashlib.sha256(f"{finding_id}|{layer}|{component}".encode()).hexdigest()[:32]
    conn.execute(
        """INSERT OR REPLACE INTO layer_verdicts
           (verdict_id, finding_id, layer, component, verdict, confidence, method, rationale)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        [vid, finding_id, layer, component, verdict, confidence, method, rationale])
    if own:
        conn.commit()
        conn.close()
    return vid


def count_by_tool(db_path=FINDINGS_DB):
    conn = get_connection(db_path)
    rows = conn.execute("SELECT source_tool, COUNT(*) FROM findings GROUP BY source_tool").fetchall()
    conn.close()
    return dict(rows)


def list_runs(db_path=FINDINGS_DB):
    conn = get_connection(db_path)
    rows = conn.execute(
        "SELECT run_id, source_tool, COUNT(*) n, MIN(created_at) t "
        "FROM findings GROUP BY run_id ORDER BY t"
    ).fetchall()
    conn.close()
    return rows