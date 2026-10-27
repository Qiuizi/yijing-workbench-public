"""安装更新前的一致性备份。

为什么不用 `copy`：
    SQLite 可能处于 WAL / 回滚日志未 checkpoint 的状态，直接复制主库文件会漏掉
    最新事务甚至得到损坏文件。这里统一走 SQLite **在线备份 API**
    （`sqlite3.Connection.backup`），它在页级加锁下产出一致快照，
    并且对正在被 sidecar 写入的库同样安全。

备份落点：`YIJING_BACKUP_DIR`（默认 <用户数据目录>/backups），
与历史库同一 Windows 用户目录，不上传、不写仓库。
"""

from __future__ import annotations

import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from backend.services.desktop_migration import DATA_TABLES

MAX_UPDATE_BACKUPS = 5
_BACKUP_PATTERN = re.compile(r"^history\.pre-update-\d{8}T\d{6}Z\.sqlite3$")


class DesktopBackupError(RuntimeError):
    """备份前置条件或完整性校验失败。"""


def _counts(connection: sqlite3.Connection) -> dict[str, int]:
    counts: dict[str, int] = {}
    for table in DATA_TABLES:
        exists = connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)
        ).fetchone()
        counts[table] = int(connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]) if exists else 0
    return counts


def _prune(directory: Path) -> None:
    """只保留最近若干份「升级前备份」，不碰导入备份与用户手写的其它文件。"""
    candidates = sorted(
        (path for path in directory.iterdir() if path.is_file() and _BACKUP_PATTERN.match(path.name)),
        key=lambda path: path.name,
        reverse=True,
    )
    for stale in candidates[MAX_UPDATE_BACKUPS:]:
        try:
            stale.unlink()
        except OSError:
            # 清理失败不影响本次备份的可用性
            pass


def create_update_backup(db_path: Path, backup_dir: Path) -> dict[str, Any]:
    """创建一份升级前的一致性快照，并校验它与源库的计数一致。"""
    if not db_path.exists():
        raise DesktopBackupError("找不到本地历史数据库，已取消安装")
    backup_dir.mkdir(parents=True, exist_ok=True)

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    destination_path = backup_dir / f"history.pre-update-{stamp}.sqlite3"

    source = sqlite3.connect(db_path, timeout=10)
    try:
        source.execute("PRAGMA busy_timeout = 5000")
        source_counts = _counts(source)

        destination = sqlite3.connect(destination_path)
        try:
            with destination:
                source.backup(destination)
            integrity = destination.execute("PRAGMA integrity_check").fetchone()
            if integrity is None or integrity[0] != "ok":
                raise DesktopBackupError("备份文件完整性检查失败，已取消安装")
            backup_counts = _counts(destination)
        finally:
            destination.close()
    except sqlite3.Error as exc:  # pragma: no cover - 仅在磁盘/锁异常时触发
        raise DesktopBackupError(f"创建数据库备份失败：{exc}") from exc
    finally:
        source.close()

    mismatched = [name for name in DATA_TABLES if source_counts.get(name) != backup_counts.get(name)]
    if mismatched:
        raise DesktopBackupError(f"备份计数与源库不一致（{', '.join(mismatched)}），已取消安装")

    _prune(backup_dir)

    return {
        "path": str(destination_path),
        "bytes": destination_path.stat().st_size,
        "history_count": backup_counts.get("divinations", 0),
        "ai_session_count": backup_counts.get("ai_sessions", 0),
        "settings_preserved": backup_counts.get("app_settings", 0) > 0,
        "created_at": stamp,
    }
