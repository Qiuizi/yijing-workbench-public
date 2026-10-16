"""Small, synthetic-only history benchmark. Run from the repository root:

    .venv/bin/python -m scripts.benchmark_history

The legacy route reproduces main d839747's list logic and response model.
Both routes run on the same temporary DB through the same TestClient.
"""
import json
import platform
import statistics
from pathlib import Path
from tempfile import TemporaryDirectory
from time import perf_counter
from unittest.mock import patch

from fastapi import Request
from fastapi.testclient import TestClient

from backend.main import create_app
from backend.models import HistoryListResponse
from backend.services import history


async def legacy_history(request: Request):
    items = []
    for row in history.list_recent(request.app.state.db_path):
        result = json.loads(row["result_json"])
        items.append({
            "id": row["id"], "question": row["question"], "method": row["method"],
            "base_name": result["base_hexagram"]["title"], "changed_name": result["changed_hexagram"]["title"],
            "moving_positions": result["moving_positions"], "created_at": row["created_at"],
            "has_ai_sessions": bool(history.list_ai_sessions(request.app.state.db_path, row["id"])),
        })
    return {"items": items, "total": len(items)}


def main():
    with TemporaryDirectory(prefix="yijing-history-benchmark-") as directory:
        path = Path(directory) / "synthetic.sqlite3"
        app = create_app(db_path=path)
        app.add_api_route("/_benchmark/legacy", legacy_history, response_model=HistoryListResponse)
        with TestClient(app) as client:
            template = client.post("/api/divination/manual", json={
                "question": "合成基准占问", "lines": [9, 7, 8, 7, 8, 7],
            }).json()
            with history.connect(path) as db:
                db.execute("DELETE FROM divinations")
                for i in range(1000):
                    record = {**template, "question": f"合成阅读计划 {i}"}
                    cursor = db.execute(
                        "INSERT INTO divinations(question,method,lines_json,result_json,created_at) VALUES (?,?,?,?,?)",
                        (record["question"], "manual", json.dumps(record["lines"]), json.dumps(record, ensure_ascii=False), "2026-10-16T00:00:00Z"),
                    )
                    if i % 3 == 0:
                        db.execute("INSERT INTO ai_sessions(divination_id,mode,model_id,context_json,created_at) VALUES (?,?,?,?,?)",
                                   (cursor.lastrowid, "classical", "synthetic", "{}", "2026-10-16T00:00:00Z"))
                print("query_plan:", [tuple(row) for row in db.execute(
                    "EXPLAIN QUERY PLAN SELECT d.id, EXISTS(SELECT 1 FROM ai_sessions a WHERE a.divination_id=d.id) "
                    "FROM divinations d ORDER BY created_at DESC,id DESC LIMIT 20")])
            db.close()
            original = history.connect
            counts = {"selects": 0, "connections": 0}
            def trace(sql):
                if sql.lstrip().upper().startswith("SELECT"):
                    counts["selects"] += 1
            def connect(db_path):
                counts["connections"] += 1
                connection = original(db_path)
                connection.set_trace_callback(trace)
                return connection
            print(f"Python {platform.python_version()}; 1000 records, 334 sessions, 1 warmup + 7 measured requests per case")
            with patch.object(history, "connect", connect):
                for label, url in [("legacy_all", "/_benchmark/legacy"), ("page20", "/api/history"),
                                   ("search_ai", "/api/history?q=阅读&ai_filter=with-ai&limit=20")]:
                    client.get(url)
                    elapsed = []
                    for _ in range(7):
                        counts.update(selects=0, connections=0)
                        start = perf_counter()
                        response = client.get(url)
                        elapsed.append((perf_counter() - start) * 1000)
                        assert response.status_code == 200
                    data = response.json()
                    print(json.dumps({"case": label, "median_ms": round(statistics.median(elapsed), 3),
                        "min_ms": round(min(elapsed), 3), "max_ms": round(max(elapsed), 3),
                        "response_bytes": len(response.content), "items": len(data["items"]), "total": data["total"], **counts}))


if __name__ == "__main__":
    main()
