"""PyRIT adapter — pairs user/assistant rows from PyRIT's memory DB."""
import os
import sqlite3
from db import get_connection, insert_finding, make_run_id

PYRIT_DB = os.path.expanduser("~/Library/Application Support/dbdata/pyrit.db")


def ingest(pyrit_db=PYRIT_DB, target_model="llama3.2:3b"):
    """Ingest PyRIT conversations. Returns number of findings inserted."""
    if not os.path.exists(pyrit_db):
        print(f"[pyrit] database not found at {pyrit_db}")
        return 0

    src = sqlite3.connect(pyrit_db)
    cur = src.cursor()

    # objectives (the real attack label) keyed by conversation
    objectives = {}
    try:
        for conv_id, objective in cur.execute(
            "SELECT conversation_id, objective FROM AttackResultEntries"
        ).fetchall():
            objectives[conv_id] = objective
    except sqlite3.Error:
        pass  # older schema / table absent — fall back to prompt text

    responses = {}
    for conv_id, text in cur.execute(
        "SELECT conversation_id, converted_value FROM PromptMemoryEntries WHERE role='assistant'"
    ).fetchall():
        responses[conv_id] = text

    user_rows = cur.execute(
        "SELECT conversation_id, converted_value FROM PromptMemoryEntries WHERE role='user'"
    ).fetchall()
    src.close()

    conn = get_connection()
    count = 0
    for conv_id, prompt in user_rows:
        response = responses.get(conv_id)
        if response is None:
            continue
        attack = objectives.get(conv_id) or prompt
        insert_finding(
            source_tool="pyrit",
            attack=attack,
            target_model=target_model,
            prompt=prompt,
            response=response,
            conn=conn,
        )
        count += 1

    conn.commit()
    conn.close()
    print(f"[pyrit] inserted {count} findings")
    return count


if __name__ == "__main__":
    ingest()
    run_id = make_run_id("pyrit", os.path.getmtime(pyrit_db))