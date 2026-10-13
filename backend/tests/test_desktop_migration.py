import hashlib
import sqlite3
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.catalog import load_catalog
from backend.main import _build_result, create_app
from backend.services import history
from backend.services.desktop_migration import DesktopMigrationError, import_legacy_database


class TestSecretStore:
    def unprotect(self, value):
        if value != "dpapi:valid":
            raise ValueError("invalid test credential")
        return "test-secret-not-real"


def make_v2_database(path: Path) -> None:
    history.initialize(path)
    catalog = load_catalog()
    result = _build_result(question="迁移测试记录", method="manual", lines=(7, 7, 7, 7, 7, 7), coin_faces=None, catalog=catalog)
    created = "2026-09-24T10:00:00+00:00"
    divination_id = history.create(path, result, created)
    session_id = history.create_ai_session(
        path, divination_id, "classical", "test-model",
        {"rule_versions": {"reading": "qiming-tongshi@1.0.0"}, "divination": result}, created,
    )
    history.add_ai_message(path, session_id, "user", "测试追问", created)
    history.add_ai_message(path, session_id, "assistant", {"answer": "测试回答"}, created)
    history.save_setting(path, "app_preferences", {"timezone": "Asia/Shanghai"}, created)
    history.save_setting(path, "deepseek_api_key_protected", "dpapi:valid", created)
    # Existing V2 installations could have no migration ledger; migration must not lose rows.
    connection = sqlite3.connect(path)
    try:
        connection.execute("DROP TABLE schema_migrations")
        connection.commit()
    finally:
        connection.close()


def test_import_migrates_and_preserves_history_sessions_settings_and_source(tmp_path):
    source = tmp_path / "web.sqlite3"
    target = tmp_path / "desktop" / "history.sqlite3"
    backup_dir = tmp_path / "desktop" / "backups"
    make_v2_database(source)
    source_hash = hashlib.sha256(source.read_bytes()).hexdigest()

    result = import_legacy_database(target, source, backup_dir, TestSecretStore())

    assert result["imported"] is True
    assert result["counts"]["divinations"] == 1
    assert result["counts"]["ai_sessions"] == 1
    assert result["counts"]["ai_messages"] == 2
    assert result["counts"]["app_settings"] == 2
    assert Path(result["backup_path"]).is_file()
    assert result["source_preserved"] is True
    assert hashlib.sha256(source.read_bytes()).hexdigest() == source_hash
    assert history.list_recent(target)[0]["question"] == "迁移测试记录"
    assert history.get_ai_session(target, 1)["model_id"] == "test-model"
    assert history.list_ai_messages(target, 1)[0]["content"] == "测试追问"
    assert history.get_setting(target, "app_preferences")["timezone"] == "Asia/Shanghai"


def test_import_rejects_nonempty_desktop_database_without_overwriting(tmp_path):
    source = tmp_path / "web.sqlite3"
    target = tmp_path / "desktop.sqlite3"
    make_v2_database(source)
    history.initialize(target)
    existing = _build_result(
        question="桌面现有记录", method="manual", lines=(8, 8, 8, 8, 8, 8), coin_faces=None, catalog=load_catalog()
    )
    history.create(target, existing, "2026-09-24T10:00:00+00:00")

    with pytest.raises(DesktopMigrationError, match="已有历史"):
        import_legacy_database(target, source, tmp_path / "backups", TestSecretStore())

    assert len(history.list_recent(target)) == 1
    assert history.list_recent(target)[0]["question"] == "桌面现有记录"
    assert list((tmp_path / "backups").glob("web-import-*.sqlite3"))


def test_import_rejects_dpapi_key_that_current_user_cannot_unprotect(tmp_path):
    source = tmp_path / "web.sqlite3"
    target = tmp_path / "desktop.sqlite3"
    make_v2_database(source)

    class WrongUser:
        def unprotect(self, _value):
            raise OSError("DPAPI user mismatch")

    with pytest.raises(DesktopMigrationError, match="DPAPI"):
        import_legacy_database(target, source, tmp_path / "backups", WrongUser())
    assert not target.exists()
    assert list((tmp_path / "backups").glob("web-import-*.sqlite3"))


def test_desktop_import_endpoint_requires_token_and_imports_user_selected_db(tmp_path):
    source = tmp_path / "web.sqlite3"
    target = tmp_path / "desktop.sqlite3"
    make_v2_database(source)
    app = create_app(db_path=target, desktop_mode=True, desktop_api_token="z" * 48, secret_store=TestSecretStore())
    with TestClient(app) as client:
        assert client.post("/api/desktop/migration/import", json={"source_path": str(source)}).status_code == 401
        response = client.post(
            "/api/desktop/migration/import",
            headers={"Authorization": f"Bearer {'z' * 48}", "Origin": "http://tauri.localhost"},
            json={"source_path": str(source)},
        )
        assert response.status_code == 200, response.text
        assert response.json()["counts"]["divinations"] == 1
        restored = client.get(
            "/api/history/1",
            headers={"Authorization": f"Bearer {'z' * 48}", "Origin": "http://tauri.localhost"},
        )
        assert restored.status_code == 200
        assert restored.json()["question"] == "迁移测试记录"
