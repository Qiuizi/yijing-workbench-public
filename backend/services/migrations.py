"""Versioned, transactional SQLite schema migrations.

Version 1 is the V2 baseline schema. It is intentionally idempotent so an
existing V1/V2 database can be stamped without rebuilding any user tables.
Subsequent schema changes use explicit ALTER TABLE migrations.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from typing import Callable


def _v1_v2_baseline(db: sqlite3.Connection) -> None:
    db.execute(
        """CREATE TABLE IF NOT EXISTS divinations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            question TEXT NOT NULL,
            method TEXT NOT NULL CHECK (method IN ('coins', 'manual')),
            lines_json TEXT NOT NULL,
            result_json TEXT NOT NULL,
            created_at TEXT NOT NULL
        )"""
    )
    db.execute("CREATE INDEX IF NOT EXISTS idx_divinations_created_at ON divinations(created_at DESC, id DESC)")
    db.execute(
        """CREATE TABLE IF NOT EXISTS divination_context (
            divination_id INTEGER PRIMARY KEY REFERENCES divinations(id) ON DELETE CASCADE,
            reading_json TEXT,
            ruleset_id TEXT,
            ruleset_version TEXT,
            najia_json TEXT,
            najia_params_json TEXT,
            updated_at TEXT NOT NULL
        )"""
    )
    db.execute(
        """CREATE TABLE IF NOT EXISTS ai_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            divination_id INTEGER NOT NULL REFERENCES divinations(id) ON DELETE CASCADE,
            mode TEXT NOT NULL CHECK (mode IN ('classical', 'najia')),
            model_id TEXT NOT NULL,
            context_json TEXT NOT NULL,
            created_at TEXT NOT NULL
        )"""
    )
    db.execute("CREATE INDEX IF NOT EXISTS idx_ai_sessions_divination ON ai_sessions(divination_id, id DESC)")
    db.execute(
        """CREATE TABLE IF NOT EXISTS ai_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER NOT NULL REFERENCES ai_sessions(id) ON DELETE CASCADE,
            role TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
            content_json TEXT NOT NULL,
            created_at TEXT NOT NULL
        )"""
    )
    db.execute("CREATE INDEX IF NOT EXISTS idx_ai_messages_session ON ai_messages(session_id, id)")
    db.execute(
        """CREATE TABLE IF NOT EXISTS app_settings (
            key TEXT PRIMARY KEY,
            value_json TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )"""
    )


def _v2_calendar_provenance(db: sqlite3.Connection) -> None:
    columns = {row[1] for row in db.execute("PRAGMA table_info(divination_context)")}
    if "calendar_context_json" not in columns:
        db.execute("ALTER TABLE divination_context ADD COLUMN calendar_context_json TEXT")


def _v3_ai_request_deduplication(db: sqlite3.Connection) -> None:
    db.execute(
        """CREATE TABLE IF NOT EXISTS ai_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER NOT NULL REFERENCES ai_sessions(id) ON DELETE CASCADE,
            request_id TEXT NOT NULL,
            message_text TEXT NOT NULL,
            regenerate_from_message_id INTEGER REFERENCES ai_messages(id) ON DELETE SET NULL,
            user_message_id INTEGER REFERENCES ai_messages(id) ON DELETE SET NULL,
            assistant_message_id INTEGER NOT NULL REFERENCES ai_messages(id) ON DELETE CASCADE,
            created_at TEXT NOT NULL,
            UNIQUE(session_id, request_id)
        )"""
    )
    db.execute("CREATE INDEX IF NOT EXISTS idx_ai_requests_session ON ai_requests(session_id, id DESC)")


def _v4_ai_request_failures(db: sqlite3.Connection) -> None:
    db.execute(
        """CREATE TABLE IF NOT EXISTS ai_request_failures (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER NOT NULL REFERENCES ai_sessions(id) ON DELETE CASCADE,
            request_id TEXT NOT NULL,
            message_text TEXT NOT NULL,
            regenerate_from_message_id INTEGER REFERENCES ai_messages(id) ON DELETE SET NULL,
            code TEXT NOT NULL,
            stage TEXT NOT NULL,
            public_message TEXT NOT NULL,
            created_at TEXT NOT NULL,
            UNIQUE(session_id, request_id)
        )"""
    )
    db.execute("CREATE INDEX IF NOT EXISTS idx_ai_request_failures_session ON ai_request_failures(session_id, id DESC)")


Migration = tuple[int, str, Callable[[sqlite3.Connection], None]]
MIGRATIONS: tuple[Migration, ...] = (
    (1, "v2-baseline-schema", _v1_v2_baseline),
    (2, "calendar-provenance", _v2_calendar_provenance),
    (3, "ai-request-idempotency", _v3_ai_request_deduplication),
    (4, "ai-request-failure-recovery", _v4_ai_request_failures),
)


def run_migrations(db: sqlite3.Connection) -> None:
    db.execute(
        """CREATE TABLE IF NOT EXISTS schema_migrations (
            version INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            applied_at TEXT NOT NULL
        )"""
    )
    db.commit()

    applied = {row[0] for row in db.execute("SELECT version FROM schema_migrations")}
    for version, name, migration in MIGRATIONS:
        if version in applied:
            continue
        try:
            db.execute("BEGIN IMMEDIATE")
            migration(db)
            applied_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
            db.execute(
                "INSERT INTO schema_migrations(version, name, applied_at) VALUES (?, ?, ?)",
                (version, name, applied_at),
            )
            db.execute(f"PRAGMA user_version = {version}")
            db.commit()
        except Exception:
            db.rollback()
            raise
