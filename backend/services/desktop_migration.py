"""Safe, opt-in import of a Web edition database into the desktop profile."""

from __future__ import annotations

import json
import os
import secrets
import sqlite3
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote
from typing import Any

from backend.services import history
from backend.services.migrations import run_migrations


DATA_TABLES = ("divinations", "divination_context", "ai_sessions", "ai_messages", "ai_requests", "app_settings")


class DesktopMigrationError(ValueError):
    """A safe import precondition or data-integrity check failed."""


def _counts(connection: sqlite3.Connection) -> dict[str, int]:
    counts: dict[str, int] = {}
    for table in DATA_TABLES:
        exists = connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)
        ).fetchone()
        counts[table] = int(connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]) if exists else 0
    return counts


def migration_status(db_path: Path) -> dict[str, Any]:
    """Report only whether the target profile can accept a one-time import."""
    if not db_path.exists():
        counts = {table: 0 for table in DATA_TABLES}
    else:
        connection = sqlite3.connect(db_path)
        try:
            counts = _counts(connection)
        finally:
            connection.close()
    return {
        "can_import": not any(counts.values()),
        "history_count": counts["divinations"],
        "ai_session_count": counts["ai_sessions"],
        "has_settings": counts["app_settings"] > 0,
    }


def _readonly_connection(path: Path) -> sqlite3.Connection:
    uri = f"file:{quote(path.as_posix(), safe='/:')}?mode=ro"
    return sqlite3.connect(uri, uri=True, timeout=10)


def _integrity_check(connection: sqlite3.Connection) -> None:
    result = connection.execute("PRAGMA integrity_check").fetchone()
    if result is None or result[0] != "ok":
        raise DesktopMigrationError("SQLite 完整性检查失败，未导入任何数据")
    if connection.execute("PRAGMA foreign_key_check").fetchone() is not None:
        raise DesktopMigrationError("旧数据库存在不完整的关联记录，未导入任何数据")


def _copy_backup(source_path: Path, backup_path: Path) -> None:
    source = _readonly_connection(source_path)
    destination = sqlite3.connect(backup_path)
    try:
        source.backup(destination)
        destination.commit()
    finally:
        destination.close()
        source.close()


def _validate_encrypted_key(connection: sqlite3.Connection, secret_store: Any) -> None:
    row = connection.execute(
        "SELECT value_json FROM app_settings WHERE key='deepseek_api_key_protected'"
    ).fetchone()
    if row is None:
        return
    try:
        protected_value = json.loads(row[0])
        if not isinstance(protected_value, str) or not secret_store.unprotect(protected_value):
            raise ValueError("empty credential")
    except Exception as exc:
        raise DesktopMigrationError(
            "旧数据库中的 DPAPI 密钥无法由当前 Windows 用户验证；未导入数据，原数据库和备份均已保留"
        ) from exc


def import_legacy_database(
    target_path: Path,
    source_path: Path,
    backup_dir: Path,
    secret_store: Any,
) -> dict[str, Any]:
    """Back up, migrate a private snapshot, then transactionally import into an empty DB.

    The user-selected source is opened read-only and is never moved, modified, or deleted.
    The desktop target is only changed by one SQLite transaction after all checks pass.
    """
    try:
        source = source_path.expanduser().resolve(strict=True)
        target = target_path.expanduser().resolve()
    except OSError as exc:
        raise DesktopMigrationError("找不到所选 SQLite 数据库文件") from exc
    if not source.is_file() or source == target:
        raise DesktopMigrationError("所选文件不是可导入的旧版数据库")

    backup_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup_path = backup_dir / f"web-import-{stamp}-{os.getpid()}-{secrets.token_hex(4)}.sqlite3"
    temporary_path: Path | None = None
    source_connection: sqlite3.Connection | None = None
    target_connection: sqlite3.Connection | None = None
    try:
        _copy_backup(source, backup_path)
        source_connection = _readonly_connection(backup_path)
        tables = {
            row[0] for row in source_connection.execute("SELECT name FROM sqlite_master WHERE type='table'")
        }
        if "divinations" not in tables:
            raise DesktopMigrationError("所选文件不包含易经项目的起卦记录表")
        _integrity_check(source_connection)
        _validate_encrypted_key(source_connection, secret_store)

        handle, temporary_name = tempfile.mkstemp(prefix="yijing-import-", suffix=".sqlite3", dir=backup_dir)
        os.close(handle)
        temporary_path = Path(temporary_name)
        source_connection.close()
        source_connection = None

        backup_connection = sqlite3.connect(backup_path)
        staged = sqlite3.connect(temporary_path)
        try:
            backup_connection.backup(staged)
            staged.commit()
        finally:
            backup_connection.close()
            staged.close()
        staged = sqlite3.connect(temporary_path)
        try:
            run_migrations(staged)
            _integrity_check(staged)
        finally:
            staged.close()

        history.initialize(target_path)
        target_connection = history.connect(target_path)
        target_connection.execute("ATTACH DATABASE ? AS legacy", (str(temporary_path),))
        target_connection.execute("BEGIN IMMEDIATE")
        target_counts = _counts(target_connection)
        if any(target_counts.values()):
            raise DesktopMigrationError("桌面版已有历史、会话或设置；为避免覆盖，无法导入旧数据")

        legacy_tables = {
            row[0] for row in target_connection.execute("SELECT name FROM legacy.sqlite_master WHERE type='table'")
        }
        legacy_counts: dict[str, int] = {}
        for table in DATA_TABLES:
            if table not in legacy_tables:
                legacy_counts[table] = 0
                continue
            source_columns = {
                row[1] for row in target_connection.execute(f"PRAGMA legacy.table_info({table})")
            }
            target_columns = {
                row[1] for row in target_connection.execute(f"PRAGMA main.table_info({table})")
            }
            columns = sorted(source_columns & target_columns)
            if table == "divinations" and not {"id", "question", "result_json"}.issubset(columns):
                raise DesktopMigrationError("旧版起卦记录表结构无法安全兼容")
            if columns:
                names = ", ".join(f'"{column}"' for column in columns)
                target_connection.execute(
                    f"INSERT INTO main.{table} ({names}) SELECT {names} FROM legacy.{table}"
                )
            legacy_counts[table] = int(
                target_connection.execute(f"SELECT COUNT(*) FROM legacy.{table}").fetchone()[0]
            )

        if legacy_counts["divinations"] == 0:
            raise DesktopMigrationError("所选数据库没有可导入的起卦记录")
        _integrity_check(target_connection)
        target_connection.commit()
        return {
            "imported": True,
            "counts": legacy_counts,
            "backup_path": str(backup_path),
            "source_preserved": True,
        }
    except DesktopMigrationError:
        if target_connection is not None:
            target_connection.rollback()
        raise
    except (sqlite3.Error, OSError, ValueError) as exc:
        if target_connection is not None:
            target_connection.rollback()
        raise DesktopMigrationError("旧数据库验证或导入失败；桌面数据未被覆盖，原文件及备份仍保留") from exc
    finally:
        if source_connection is not None:
            source_connection.close()
        if target_connection is not None:
            try:
                target_connection.execute("DETACH DATABASE legacy")
            except sqlite3.Error:
                pass
            target_connection.close()
        if temporary_path is not None:
            try:
                temporary_path.unlink(missing_ok=True)
                Path(f"{temporary_path}-wal").unlink(missing_ok=True)
                Path(f"{temporary_path}-shm").unlink(missing_ok=True)
            except OSError:
                pass
