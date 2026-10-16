"""History list contract tests; every database is synthetic and temporary."""
import json

import pytest
from fastapi.testclient import TestClient

from backend.main import create_app
from backend.services import history


def seed(path, count):
    db = history.connect(path)
    try:
        for i in range(count):
            question = f"合成阅读计划 {i}"
            result = {"base_hexagram": {"title": "乾"}, "changed_hexagram": {"title": "姤"}, "moving_positions": [1]}
            cursor = db.execute(
                "INSERT INTO divinations(question,method,lines_json,result_json,created_at) VALUES (?,?,?,?,?)",
                (question, "manual", "[]", json.dumps(result), "2026-10-16T00:00:00Z"),
            )
            if i % 2 == 0:
                # Multiple sessions must still count as just one matching record.
                for _ in range(2):
                    db.execute(
                        "INSERT INTO ai_sessions(divination_id,mode,model_id,context_json,created_at) VALUES (?,?,?,?,?)",
                        (cursor.lastrowid, "classical", "synthetic", "{}", "2026-10-16T00:00:00Z"),
                    )
        db.commit()
    finally:
        db.close()


@pytest.mark.parametrize("count", [0, 1, 20, 21, 105])
def test_default_bounded_pages_and_stable_equal_timestamp_order(tmp_path, count):
    path = tmp_path / "history.sqlite3"
    with TestClient(create_app(db_path=path)) as client:
        seed(path, count)
        response = client.get("/api/history")
        assert response.status_code == 200
        assert response.json()["total"] == count
        assert [r["id"] for r in response.json()["items"]] == list(range(count, max(0, count - 20), -1))
        seen = []
        for offset in range(0, count, 20):
            page = client.get("/api/history", params={"limit": 20, "offset": offset}).json()
            assert page["total"] == count
            seen.extend(item["id"] for item in page["items"])
        assert seen == list(range(count, 0, -1))
        assert client.get("/api/history", params={"offset": count}).json() == {"items": [], "total": count}


def test_search_filters_literals_and_accurate_totals(tmp_path):
    path = tmp_path / "history.sqlite3"
    with TestClient(create_app(db_path=path)) as client:
        seed(path, 21)
        for ai_filter, expected in [("all", 21), ("with-ai", 11), ("without-ai", 10)]:
            response = client.get("/api/history", params={"q": " 阅读计划 ", "ai_filter": ai_filter, "limit": 3})
            assert response.status_code == 200
            data = response.json()
            assert data["total"] == expected
            assert len(data["items"]) == 3
            if ai_filter != "all":
                assert all(item["has_ai_sessions"] == (ai_filter == "with-ai") for item in data["items"])
        assert client.get("/api/history", params={"q": "不存在"}).json() == {"items": [], "total": 0}
        assert client.get("/api/history", params={"q": "计划 20", "ai_filter": "without-ai"}).json()["total"] == 0
        special = "Alpha 100%_\\' OR 1=1 -- 中文"
        db = history.connect(path)
        db.execute("UPDATE divinations SET question=? WHERE id=1", (special,))
        db.commit()
        db.close()
        for query in ["alpha", "%", "_", "\\", "' OR 1=1 --"]:
            found = client.get("/api/history", params={"q": query}).json()
            assert found["total"] == 1
            assert found["items"][0]["id"] == 1


@pytest.mark.parametrize("params", [
    {"limit": 0}, {"limit": -1}, {"limit": 101}, {"limit": "x"}, {"limit": "1.5"},
    {"offset": -1}, {"offset": 1_000_001}, {"offset": "x"}, {"offset": "1.5"},
    {"ai_filter": "invalid"}, {"q": "长" * 501},
])
def test_invalid_query_parameters(tmp_path, params):
    with TestClient(create_app(db_path=tmp_path / "history.sqlite3")) as client:
        assert client.get("/api/history", params=params).status_code == 422


def test_limit_and_offset_upper_bound_and_delete_last_page(tmp_path):
    path = tmp_path / "history.sqlite3"
    with TestClient(create_app(db_path=path)) as client:
        seed(path, 21)
        assert len(client.get("/api/history", params={"limit": 100}).json()["items"]) == 21
        assert client.get("/api/history", params={"offset": 1_000_000}).json() == {"items": [], "total": 21}
        last = client.get("/api/history", params={"offset": 20}).json()["items"][0]
        assert client.delete(f"/api/history/{last['id']}").status_code == 204
        assert client.get("/api/history", params={"offset": 20}).json() == {"items": [], "total": 20}
        assert len(client.get("/api/history").json()["items"]) == 20


def test_constant_query_count_and_unchanged_detail_and_payload(tmp_path, monkeypatch):
    path = tmp_path / "history.sqlite3"
    with TestClient(create_app(db_path=path)) as client:
        # A complete real-shaped synthetic result also exercises detail/export compatibility.
        created = client.post("/api/divination/manual", json={"question": "合成导出兼容", "lines": [9, 7, 8, 7, 8, 7]}).json()
        seed(path, 300)
        statements = []
        connections = []
        original = history.connect
        def connect(db_path):
            db = original(db_path)
            connections.append(db_path)
            db.set_trace_callback(statements.append)
            return db
        def no_n_plus_one(*args, **kwargs):
            raise AssertionError("History list must not hydrate sessions per row")
        monkeypatch.setattr(history, "connect", connect)
        with monkeypatch.context() as patch:
            patch.setattr(history, "list_ai_sessions", no_n_plus_one)
            response = client.get("/api/history", params={"ai_filter": "with-ai", "q": "合成"})
        assert response.status_code == 200
        assert response.json()["total"] == 150
        assert len(connections) == 1
        assert len([s for s in statements if s.startswith("SELECT")]) == 2
        detail = client.get(f"/api/history/{created['id']}").json()
        assert detail["question"] == created["question"]
        assert detail["lines"] == created["lines"]
        assert detail["base_hexagram"] == created["base_hexagram"]
        assert detail["traditional_reading"] == created["traditional_reading"]
        assert detail["ai_sessions"] == []
        db = original(path)
        before = db.execute("SELECT result_json FROM divinations WHERE id=?", (created["id"],)).fetchone()[0]
        client.get("/api/history", params={"q": "合成导出", "limit": 1})
        after = db.execute("SELECT result_json FROM divinations WHERE id=?", (created["id"],)).fetchone()[0]
        assert before == after
        db.close()
