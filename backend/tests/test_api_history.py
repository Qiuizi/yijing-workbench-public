from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
import sqlite3

import pytest
from fastapi.testclient import TestClient

from backend.catalog import load_catalog
from backend.main import create_app
from backend.services import history


def test_manual_divination_and_history_lifecycle(tmp_path):
    app = create_app(db_path=tmp_path / "test.sqlite3", catalog=load_catalog())
    with TestClient(app) as client:
        response = client.post("/api/divination/manual", json={"question": "核对姤卦", "lines": [9, 7, 7, 7, 7, 7]})
        assert response.status_code == 200
        result = response.json()
        assert result["base_hexagram"]["title"] == "乾为天"
        assert result["changed_hexagram"]["name"] == "姤"
        assert result["changed_hexagram"]["binary_code"] == "111110"
        assert result["moving_positions"] == [1]
        assert [line["position"] for line in result["lines"]] == [1, 2, 3, 4, 5, 6]
        assert [line["position"] for line in result["changed_lines"]] == [1, 2, 3, 4, 5, 6]
        assert result["changed_lines"][0]["yin_yang"] == "阴"
        assert result["lines"][0]["coins"] is None

        listing = client.get("/api/history")
        assert listing.status_code == 200
        assert listing.json()["total"] == 1
        assert listing.json()["items"][0]["base_name"] == "乾为天"

        detail = client.get(f"/api/history/{result['id']}")
        assert detail.status_code == 200
        assert detail.json()["lines"] == result["lines"]
        assert detail.json()["changed_hexagram"]["title"] == "天风姤"

        deleted = client.delete(f"/api/history/{result['id']}")
        assert deleted.status_code == 204
        assert client.get(f"/api/history/{result['id']}").status_code == 404
        assert client.get("/api/history").json()["total"] == 0


def test_coin_api_returns_replayable_toss_details_and_persists(tmp_path):
    app = create_app(db_path=tmp_path / "coins.sqlite3")
    with TestClient(app) as client:
        response = client.post("/api/divination", json={"question": "看一看眼前的选择"})
        assert response.status_code == 200
        data = response.json()
        assert data["method"] == "coins"
        assert len(data["lines"]) == 6
        for line in data["lines"]:
            assert len(line["coins"]) == 3
            assert set(line["coins"]) <= {2, 3}
            assert sum(line["coins"]) == line["value"]
        assert client.get(f"/api/history/{data['id']}").status_code == 200


def test_invalid_manual_input_has_unified_error_shape(tmp_path):
    app = create_app(db_path=tmp_path / "invalid.sqlite3")
    with TestClient(app) as client:
        for lines in ([7] * 5, [6, 7, 8, 9, 7, 5], [6, 7, 8, 9, 7, 7.0]):
            response = client.post("/api/divination/manual", json={"question": "测试", "lines": lines})
            assert response.status_code == 422
            assert response.json()["error"]["code"] == "VALIDATION_ERROR"
            assert response.json()["error"]["message"] == "请求参数无效"
        blank = client.post("/api/divination", json={"question": "   "})
        assert blank.status_code == 422
        assert blank.json()["error"]["code"] == "VALIDATION_ERROR"


@pytest.mark.parametrize(
    ("lines", "hexagram_id", "special_name", "special_text"),
    [
        ([9, 9, 9, 9, 9, 9], 1, "用九", "用九：見羣龍无首，吉。"),
        ([6, 6, 6, 6, 6, 6], 2, "用六", "用六：利永貞。"),
    ],
)
def test_all_old_lines_expose_special_text_without_adding_a_seventh_line(
    tmp_path, lines, hexagram_id, special_name, special_text
):
    app = create_app(db_path=tmp_path / f"special-{hexagram_id}.sqlite3")
    with TestClient(app) as client:
        response = client.post("/api/divination/manual", json={"question": "核对特殊爻辞", "lines": lines})
        assert response.status_code == 200
        data = response.json()
        base = data["base_hexagram"]

        assert base["wenwang_order"] == hexagram_id
        assert base["special_line"]["name"] == special_name
        assert base["special_line"]["text"] == special_text
        assert base["special_line"]["source_url"] == base["source_url"]
        assert len(data["lines"]) == 6
        assert len(base["line_texts"]) == 6


def test_special_text_remains_separate_from_regular_line_texts(tmp_path):
    app = create_app(db_path=tmp_path / "regular.sqlite3")
    with TestClient(app) as client:
        response = client.post(
            "/api/divination/manual",
            json={"question": "普通乾卦", "lines": [7, 7, 7, 7, 7, 7]},
        )
        assert response.status_code == 200
        base = response.json()["base_hexagram"]
        assert len(base["line_texts"]) == 6
        assert "用九：見羣龍无首，吉。" not in base["line_texts"]


def test_legacy_history_without_provenance_or_special_lines_remains_readable(tmp_path):
    db_path = tmp_path / "legacy.sqlite3"
    history.initialize(db_path)
    legacy_hexagram = {
        "wenwang_order": 1,
        "name": "乾",
        "title": "乾为天",
        "binary_code": "111111",
        "upper_trigram": {"name": "乾", "symbol": "☰", "binary_code": "111", "image": "天"},
        "lower_trigram": {"name": "乾", "symbol": "☰", "binary_code": "111", "image": "天"},
        "judgment": "乾：元亨。利貞。",
        "line_texts": ["初九：潛龍勿用。"] * 6,
        "text_source": "旧版记录",
        "source_url": "https://zh.wikisource.org/wiki/周易/乾",
    }
    created_at = datetime(2026, 1, 1, tzinfo=timezone.utc).isoformat()
    record_id = history.create(
        db_path,
        {
            "question": "旧历史记录",
            "method": "manual",
            "lines": [],
            "changed_lines": [],
            "moving_positions": [],
            "base_hexagram": legacy_hexagram,
            "changed_hexagram": legacy_hexagram,
        },
        created_at,
    )
    app = create_app(db_path=db_path)

    with TestClient(app) as client:
        response = client.get(f"/api/history/{record_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["base_hexagram"]["title"] == "乾为天"
        assert data["base_hexagram"]["source_revision_id"] is None
        assert data["base_hexagram"]["special_line"] is None


def test_all_catalog_entries_can_be_queried(tmp_path):
    app = create_app(db_path=tmp_path / "catalog.sqlite3")
    with TestClient(app) as client:
        for hexagram_id in range(1, 65):
            response = client.get(f"/api/hexagrams/{hexagram_id}")
            assert response.status_code == 200
            data = response.json()
            assert data["wenwang_order"] == hexagram_id
            assert len(data["line_texts"]) == 6
            assert data["source_url"].startswith("https://zh.wikisource.org/")
            assert data["source_url"].endswith(f"oldid={data['source_revision_id']}")
        assert client.get("/api/hexagrams/65").status_code == 404


def test_history_lists_records_beyond_one_hundred(tmp_path):
    db_path = tmp_path / "long-history.sqlite3"
    history.initialize(db_path)
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    for index in range(105):
        history.create(
            db_path,
            {
                "question": f"第 {index + 1} 条记录",
                "method": "manual",
                "lines": [],
                "moving_positions": [],
                "base_hexagram": {"title": "乾为天"},
                "changed_hexagram": {"title": "乾为天"},
            },
            (start + timedelta(seconds=index)).isoformat(),
        )

    app = create_app(db_path=db_path)
    with TestClient(app) as client:
        listing = client.get("/api/history")
        assert listing.status_code == 200
        assert listing.json()["total"] == 105
        assert len(listing.json()["items"]) == 105
        assert listing.json()["items"][0]["question"] == "第 105 条记录"


def test_najia_chart_is_persisted_with_manual_calendar_parameters_and_cascades(tmp_path):
    db_path = tmp_path / "najia-history.sqlite3"
    app = create_app(db_path=db_path)
    with TestClient(app) as client:
        created = client.post(
            "/api/divination/manual",
            json={"question": "验证纳甲", "lines": [9, 7, 7, 7, 7, 7]},
        ).json()
        response = client.post(
            f"/api/history/{created['id']}/najia",
            json={"day_ganzhi": "甲子", "month_branch": "子"},
        )
        assert response.status_code == 200
        chart = response.json()
        assert chart["day_ganzhi"] == "甲子"
        assert chart["month_branch"] == "子"
        assert chart["xunkong"] == ["戌", "亥"]
        assert chart["base"]["hexagram_title"] == "乾为天"
        assert chart["changed"]["hexagram_title"] == "天风姤"
        assert chart["base"]["lines"][2]["role"] == "应"

        detail = client.get(f"/api/history/{created['id']}")
        assert detail.status_code == 200
        assert detail.json()["najia_chart"] == chart
        assert detail.json()["traditional_reading"]["ruleset_id"] == "qiming-tongshi"

        assert client.delete(f"/api/history/{created['id']}").status_code == 204
        assert history.get_divination_context(db_path, created["id"]) is None


def test_najia_api_rejects_invalid_ganzhi_and_month_branch(tmp_path):
    app = create_app(db_path=tmp_path / "invalid-najia.sqlite3")
    with TestClient(app) as client:
        created = client.post(
            "/api/divination/manual",
            json={"question": "无效排盘输入", "lines": [7] * 6},
        ).json()
        for body in (
            {"day_ganzhi": "甲丑", "month_branch": "子"},
            {"day_ganzhi": "甲子", "month_branch": "无"},
        ):
            response = client.post(f"/api/history/{created['id']}/najia", json=body)
            assert response.status_code == 422
            assert response.json()["error"]["code"] == "REQUEST_ERROR"


def test_najia_analysis_options_are_saved_with_versioned_results_and_leave_chart_intact(tmp_path):
    db_path = tmp_path / "najia-analysis.sqlite3"
    app = create_app(db_path=db_path)
    with TestClient(app) as client:
        created = client.post(
            "/api/divination/manual",
            json={"question": "独立测试排盘分析", "lines": [9, 7, 7, 7, 7, 7]},
        ).json()
        response = client.post(
            f"/api/history/{created['id']}/najia",
            json={
                "day_ganzhi": "甲子",
                "month_branch": "午",
                "analysis": {
                    "enabled": {
                        "use_god": True,
                        "time_relations": True,
                        "branch_relations": True,
                        "moving_changes": True,
                    },
                    "question_category": "wealth_spouse",
                    "manual_use_god_candidate": "line:2",
                },
            },
        )
        assert response.status_code == 200
        chart = response.json()
        assert chart["base"]["hexagram_title"] == "乾为天"
        assert chart["changed"]["hexagram_title"] == "天风姤"
        assert len(chart["base"]["lines"]) == 6
        assert chart["rule_analysis"]["ruleset"] == {
            "id": "zengshan-buyi-relations",
            "version": "1.0.0",
        }
        assert chart["rule_analysis"]["modules"]["use_god"]["results"]["selection_basis"] == "manual"
        assert chart["rule_analysis"]["modules"]["moving_changes"]["results"]["transitions"][0]["position"] == 1

        restored = client.get(f"/api/history/{created['id']}").json()
        assert restored["najia_chart"] == chart
        saved = history.get_divination_context(db_path, created["id"])
        assert saved["najia_params"]["analysis"]["question_category"] == "wealth_spouse"
        assert saved["najia_params"]["analysis"]["enabled"]["time_relations"] is True


def test_najia_analysis_switches_validate_independently_and_default_off(tmp_path):
    app = create_app(db_path=tmp_path / "najia-analysis-switches.sqlite3")
    with TestClient(app) as client:
        created = client.post(
            "/api/divination/manual", json={"question": "排盘分析开关", "lines": [7] * 6}
        ).json()
        default_chart = client.post(
            f"/api/history/{created['id']}/najia",
            json={"day_ganzhi": "甲子", "month_branch": "子"},
        ).json()
        modules = default_chart["rule_analysis"]["modules"]
        assert all(module is None for module in modules.values())

        for invalid in (
            {"day_ganzhi": "甲子", "month_branch": "子", "analysis": {"question_category": "wealth_spouse"}},
            {"day_ganzhi": "甲子", "month_branch": "子", "analysis": {"enabled": {"unexpected": True}}},
            {"day_ganzhi": "甲子", "month_branch": "子", "analysis": {"enabled": {"use_god": True}, "manual_use_god_candidate": "unknown:10"}},
        ):
            response = client.post(f"/api/history/{created['id']}/najia", json=invalid)
            assert response.status_code == 422


def test_automatic_calendar_inputs_are_saved_and_restored_with_full_provenance(tmp_path):
    db_path = tmp_path / "automatic-calendar.sqlite3"
    app = create_app(db_path=db_path)
    with TestClient(app) as client:
        created = client.post(
            "/api/divination/manual",
            json={"question": "测试自动历法", "lines": [9, 7, 7, 7, 7, 7]},
        ).json()
        response = client.post(
            f"/api/history/{created['id']}/najia",
            json={
                "source": "automatic",
                "local_datetime": "2025-02-03T22:12",
                "timezone": "Asia/Shanghai",
            },
        )
        assert response.status_code == 200
        chart = response.json()
        assert chart["timestamp_source"] == "automatic"
        assert chart["day_ganzhi"] == "癸卯"
        assert chart["month_branch"] == "寅"
        assert chart["calendar_context"]["local_datetime"] == "2025-02-03T22:12"
        assert chart["calendar_context"]["utc_instant"] == "2025-02-03T14:12:00Z"
        assert chart["calendar_context"]["ruleset_version"] == "1.0.0"

        saved_context = history.get_divination_context(db_path, created["id"])
        assert saved_context["calendar_context"] == chart["calendar_context"]
        assert {key: value for key, value in saved_context["najia_params"].items() if key != "analysis"} == {
            "source": "automatic",
            "local_datetime": "2025-02-03T22:12",
            "timezone": "Asia/Shanghai",
        }
        assert all(value is False for value in saved_context["najia_params"]["analysis"]["enabled"].values())
        restored = client.get(f"/api/history/{created['id']}").json()
        assert restored["najia_chart"] == chart


def test_automatic_calendar_api_rejects_dst_ambiguity_and_partial_modes(tmp_path):
    app = create_app(db_path=tmp_path / "automatic-invalid.sqlite3")
    with TestClient(app) as client:
        created = client.post(
            "/api/divination/manual", json={"question": "时区边界测试", "lines": [7] * 6}
        ).json()
        dst = client.post(
            f"/api/history/{created['id']}/najia",
            json={"source": "automatic", "local_datetime": "2025-03-09T02:30", "timezone": "America/New_York"},
        )
        assert dst.status_code == 422
        assert "夏令时" in dst.json()["error"]["message"]
        mixed = client.post(
            f"/api/history/{created['id']}/najia",
            json={
                "source": "automatic", "local_datetime": "2025-02-03T22:12",
                "timezone": "Asia/Shanghai", "day_ganzhi": "甲子", "month_branch": "子",
            },
        )
        assert mixed.status_code == 422


def test_additive_v2_migration_preserves_preexisting_v1_database_rows(tmp_path):
    db_path = tmp_path / "v1-before-migration.sqlite3"
    legacy_hexagram = {
        "wenwang_order": 1, "name": "乾", "title": "乾为天", "binary_code": "111111",
        "upper_trigram": {"name": "乾", "symbol": "☰", "binary_code": "111", "image": "天"},
        "lower_trigram": {"name": "乾", "symbol": "☰", "binary_code": "111", "image": "天"},
        "judgment": "乾：元亨。利貞。", "line_texts": ["初九：潛龍勿用。"] * 6,
        "text_source": "旧版记录", "source_url": "https://zh.wikisource.org/wiki/周易/乾",
    }
    legacy_result = {
        "question": "V1 迁移数据", "method": "manual",
        "lines": [{"position": index + 1, "value": 7, "yin_yang": "阳", "changing": False, "coins": None} for index in range(6)],
        "changed_lines": [{"position": index + 1, "value": 7, "yin_yang": "阳", "changing": False, "coins": None} for index in range(6)],
        "moving_positions": [], "base_hexagram": legacy_hexagram, "changed_hexagram": legacy_hexagram,
    }
    created_at = "2025-03-01T00:00:00+00:00"
    with sqlite3.connect(db_path) as db:
        db.execute(
            """CREATE TABLE divinations (
                id INTEGER PRIMARY KEY AUTOINCREMENT, question TEXT NOT NULL,
                method TEXT NOT NULL CHECK(method IN ('coins','manual')), lines_json TEXT NOT NULL,
                result_json TEXT NOT NULL, created_at TEXT NOT NULL)"""
        )
        db.execute(
            "INSERT INTO divinations(question, method, lines_json, result_json, created_at) VALUES(?,?,?,?,?)",
            (legacy_result["question"], "manual", json.dumps(legacy_result["lines"]), json.dumps(legacy_result), created_at),
        )

    history.initialize(db_path)
    with history.connect(db_path) as db:
        preserved = db.execute("SELECT question, result_json FROM divinations WHERE id=1").fetchone()
        assert preserved["question"] == "V1 迁移数据"
        assert json.loads(preserved["result_json"])["lines"][0]["value"] == 7
        assert db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='ai_sessions'").fetchone()
        assert db.execute("PRAGMA user_version").fetchone()[0] == 4
        assert "calendar_context_json" in {
            row[1] for row in db.execute("PRAGMA table_info(divination_context)")
        }
        assert [row[0] for row in db.execute("SELECT version FROM schema_migrations ORDER BY version")] == [1, 2, 3, 4]
        assert db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='ai_requests'").fetchone()
        assert db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='ai_request_failures'").fetchone()

    app = create_app(db_path=db_path)
    with TestClient(app) as client:
        detail = client.get("/api/history/1")
        assert detail.status_code == 200
        assert detail.json()["question"] == "V1 迁移数据"
        assert detail.json()["traditional_reading"]["ruleset_id"] == "qiming-tongshi"


def test_versioned_migration_preserves_unversioned_v2_context_sessions_messages_and_settings(tmp_path):
    db_path = tmp_path / "v2-before-migration.sqlite3"
    history.initialize(db_path)
    created_at = "2025-03-01T00:00:00+00:00"
    record_id = history.create(
        db_path,
        {
            "question": "合成的 V2 兼容样例", "method": "manual", "lines": [],
            "moving_positions": [], "base_hexagram": {"title": "乾为天"},
            "changed_hexagram": {"title": "乾为天"},
        },
        created_at,
    )
    history.save_najia_context(
        db_path, record_id, {"day_ganzhi": "甲子"}, {"day_ganzhi": "甲子", "month_branch": "子"}, created_at
    )
    session_id = history.create_ai_session(
        db_path, record_id, "classical", "mock-model", {"frozen": "V2 context"}, created_at
    )
    history.add_ai_message(db_path, session_id, "user", "合成测试消息", created_at)
    history.add_ai_message(db_path, session_id, "assistant", {"overview": "合成结果"}, created_at)
    history.save_setting(db_path, "ai_public_settings", {"ai_enabled": False, "model_id": "mock-model"}, created_at)

    # Recreate the unversioned V2 schema while leaving existing user records intact.
    with history.connect(db_path) as db:
        db.execute("ALTER TABLE divination_context DROP COLUMN calendar_context_json")
        db.execute("DROP TABLE ai_request_failures")
        db.execute("DROP TABLE ai_requests")
        db.execute("DROP TABLE schema_migrations")
        db.execute("PRAGMA user_version = 0")

    history.initialize(db_path)
    assert history.get(db_path, record_id)["question"] == "合成的 V2 兼容样例"
    context = history.get_divination_context(db_path, record_id)
    assert context["najia_chart"] == {"day_ganzhi": "甲子"}
    assert context["najia_params"] == {"day_ganzhi": "甲子", "month_branch": "子"}
    assert context["calendar_context"] is None
    assert history.get_ai_session(db_path, session_id)["context"] == {"frozen": "V2 context"}
    assert [message["role"] for message in history.list_ai_messages(db_path, session_id)] == ["user", "assistant"]
    assert history.get_setting(db_path, "ai_public_settings")["model_id"] == "mock-model"
    with history.connect(db_path) as db:
        assert db.execute("PRAGMA user_version").fetchone()[0] == 4
        assert db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='ai_requests'").fetchone()
        assert db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='ai_request_failures'").fetchone()


def test_v3_database_upgrade_adds_failure_status_without_rewriting_history(tmp_path):
    db_path = tmp_path / "v3-before-migration.sqlite3"
    history.initialize(db_path)
    record_id = history.create(
        db_path,
        {"question": "迁移保留记录", "method": "manual", "lines": [], "moving_positions": [],
         "base_hexagram": {"title": "谦为地山"}, "changed_hexagram": {"title": "谦为地山"}},
        "2026-09-25T00:00:00+00:00",
    )
    session_id = history.create_ai_session(
        db_path, record_id, "classical", "deepseek-v4-pro", {"frozen": "existing"},
        "2026-09-25T00:00:00+00:00",
    )
    history.add_ai_message(db_path, session_id, "user", "已有会话", "2026-09-25T00:00:01+00:00")
    history.add_ai_message(db_path, session_id, "assistant", {"overview": "已有回答"}, "2026-09-25T00:00:02+00:00")
    history.save_setting(db_path, "existing_setting", {"keep": True}, "2026-09-25T00:00:03+00:00")
    with history.connect(db_path) as db:
        db.execute("DROP TABLE ai_request_failures")
        db.execute("DELETE FROM schema_migrations WHERE version = 4")
        db.execute("PRAGMA user_version = 3")

    history.initialize(db_path)

    assert history.get(db_path, record_id)["question"] == "迁移保留记录"
    assert [item["role"] for item in history.list_ai_messages(db_path, session_id)] == ["user", "assistant"]
    assert history.get_setting(db_path, "existing_setting") == {"keep": True}
    assert history.list_ai_request_failures(db_path, session_id) == []
    with history.connect(db_path) as db:
        assert db.execute("PRAGMA user_version").fetchone()[0] == 4
        assert [row[0] for row in db.execute("SELECT version FROM schema_migrations ORDER BY version")] == [1, 2, 3, 4]


def test_preferences_persist_default_cast_method_without_changing_reading_ruleset(tmp_path):
    app = create_app(db_path=tmp_path / "preferences.sqlite3")
    with TestClient(app) as client:
        assert client.get("/api/preferences").json() == {
            "default_method": "coins", "timezone": "Asia/Shanghai",
            "ai_default_mode": "classical",
            "ruleset_id": "qiming-tongshi", "ruleset_version": "1.0.0"
        }
        saved = client.put("/api/preferences", json={"default_method": "manual", "timezone": "UTC", "ai_default_mode": "najia"})
        assert saved.status_code == 200
        assert saved.json()["default_method"] == "manual"
        assert saved.json()["timezone"] == "UTC"
        assert saved.json()["ai_default_mode"] == "najia"
        legacy_update = client.put("/api/preferences", json={"default_method": "coins", "timezone": "UTC"})
        assert legacy_update.json()["ai_default_mode"] == "najia"
        assert saved.json()["ruleset_id"] == "qiming-tongshi"
        invalid_timezone = client.put("/api/preferences", json={"default_method": "manual", "timezone": "No/SuchZone"})
        assert invalid_timezone.status_code == 422
        invalid = client.put("/api/preferences", json={"default_method": "yarrow"})
        assert invalid.status_code == 422
