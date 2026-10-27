"""升级前备份：一致性、WAL 场景、计数校验与清理策略。"""

import sqlite3

import pytest

from backend.services import history
from backend.services.desktop_backup import (
    MAX_UPDATE_BACKUPS,
    DesktopBackupError,
    create_update_backup,
)

RESULT = {
    "question": "升级前记录",
    "method": "manual",
    "lines": [7, 7, 7, 7, 7, 7],
    "coins": None,
    "base_id": 1,
    "changed_id": 1,
    "changing_lines": [],
}


def _seed(db_path, question="升级前记录"):
    history.initialize(db_path)
    history.create(db_path, {**RESULT, "question": question}, "2026-10-27T00:00:00+00:00")


def _backup_path(result):
    return result["path"]


def test_backup_matches_source_counts_and_passes_integrity(tmp_path):
    db_path = tmp_path / "history.sqlite3"
    backups = tmp_path / "backups"
    _seed(db_path, "第一条")
    _seed(db_path, "第二条")

    result = create_update_backup(db_path, backups)

    from pathlib import Path

    backup_path = Path(_backup_path(result))
    assert backup_path.exists()
    assert result["bytes"] == backup_path.stat().st_size
    assert result["history_count"] == 2

    connection = sqlite3.connect(backup_path)
    try:
        assert connection.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        questions = [row[0] for row in connection.execute("SELECT question FROM divinations").fetchall()]
        assert set(questions) == {"第一条", "第二条"}
    finally:
        connection.close()


def test_backup_captures_uncheckpointed_wal_rows(tmp_path):
    """WAL 模式下尚未 checkpoint 的写入，也必须出现在备份里。"""
    from pathlib import Path

    db_path = tmp_path / "history.sqlite3"
    backups = tmp_path / "backups"
    _seed(db_path, "已落盘")

    # 保持一个常驻连接，避免其它连接关闭时自动 checkpoint 把 WAL 合并回主库
    keeper = sqlite3.connect(db_path)
    try:
        keeper.execute("PRAGMA journal_mode=WAL")
        keeper.execute("PRAGMA wal_autocheckpoint=0")
        _seed(db_path, "只在 WAL 里")

        result = create_update_backup(db_path, backups)
        assert result["history_count"] == 2

        reader = sqlite3.connect(Path(_backup_path(result)))
        try:
            questions = [row[0] for row in reader.execute("SELECT question FROM divinations").fetchall()]
        finally:
            reader.close()
        assert "只在 WAL 里" in questions
    finally:
        keeper.close()


def test_backup_keeps_only_the_newest_files(tmp_path):
    db_path = tmp_path / "history.sqlite3"
    backups = tmp_path / "backups"
    backups.mkdir()
    _seed(db_path)

    for index in range(MAX_UPDATE_BACKUPS + 3):
        stale = backups / f"history.pre-update-2026010{index}T00000{index}Z.sqlite3"
        stale.write_bytes(b"stale")
    (backups / "history.import-keep-me.sqlite3").write_bytes(b"keep")

    create_update_backup(db_path, backups)

    remaining = sorted(path.name for path in backups.glob("history.pre-update-*.sqlite3"))
    assert len(remaining) == MAX_UPDATE_BACKUPS
    assert (backups / "history.import-keep-me.sqlite3").exists()


def test_missing_database_refuses_to_install(tmp_path):
    with pytest.raises(DesktopBackupError) as error:
        create_update_backup(tmp_path / "missing.sqlite3", tmp_path / "backups")
    assert "找不到本地历史数据库" in str(error.value)
