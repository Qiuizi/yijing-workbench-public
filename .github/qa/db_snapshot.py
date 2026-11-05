"""Read-only snapshot of the isolated official app database on the QA runner."""
from __future__ import annotations

import json
import os
import sqlite3
import sys
from pathlib import Path

label = sys.argv[1] if len(sys.argv) > 1 else "snapshot"
data = Path(os.environ["LOCALAPPDATA"]) / "cn.yijing.workbench"
db = data / "history.sqlite3"
out: dict = {"label": label, "db_exists": db.exists(), "db_path": str(db)}
if db.exists():
    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    try:
        out["integrity"] = con.execute("PRAGMA integrity_check").fetchone()[0]
        tables = [r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")]
        out["counts"] = {t: con.execute(f'SELECT COUNT(*) FROM "{t}"').fetchone()[0] for t in tables}
        out["questions"] = [r[0] for r in con.execute("SELECT question FROM divinations ORDER BY id")]
        settings = dict(con.execute("SELECT key, value_json FROM app_settings"))
        out["setting_keys"] = sorted(settings)
        out["key_row_present"] = "deepseek_api_key_protected" in settings
        out["app_preferences"] = settings.get("app_preferences")
    finally:
        con.close()
evidence = Path(os.environ["QA_EVIDENCE"])
evidence.mkdir(parents=True, exist_ok=True)
(evidence / f"{label}.json").write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps({
    "label": label,
    "integrity": out.get("integrity"),
    "questions": out.get("questions"),
    "key_row_present": out.get("key_row_present"),
    "app_preferences": out.get("app_preferences"),
}, ensure_ascii=False))
