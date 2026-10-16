"""Small SQLite persistence layer; it has no dependency on FastAPI."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from backend.services.migrations import run_migrations


def connect(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def initialize(db_path: Path) -> None:
    db = connect(db_path)
    try:
        run_migrations(db)
    finally:
        db.close()


def create(db_path: Path, result: dict[str, Any], created_at: str) -> int:
    db = connect(db_path)
    try:
        cursor = db.execute(
            "INSERT INTO divinations(question, method, lines_json, result_json, created_at) VALUES (?, ?, ?, ?, ?)",
            (
                result["question"],
                result["method"],
                json.dumps(result["lines"], ensure_ascii=False),
                json.dumps(result, ensure_ascii=False),
                created_at,
            ),
        )
        record_id = int(cursor.lastrowid)
        reading = result.get("traditional_reading")
        if reading:
            db.execute(
                """INSERT INTO divination_context(
                    divination_id, reading_json, ruleset_id, ruleset_version, updated_at
                ) VALUES (?, ?, ?, ?, ?)""",
                (
                    record_id,
                    json.dumps(reading, ensure_ascii=False),
                    reading.get("ruleset_id"),
                    reading.get("ruleset_version"),
                    created_at,
                ),
            )
        db.commit()
        return record_id
    finally:
        db.close()


def list_recent(db_path: Path) -> list[sqlite3.Row]:
    db = connect(db_path)
    try:
        return db.execute(
            "SELECT id, question, method, result_json, created_at FROM divinations ORDER BY created_at DESC, id DESC"
        ).fetchall()
    finally:
        db.close()


def list_page(
    db_path: Path, *, q: str = "", ai_filter: str = "all", limit: int = 20, offset: int = 0,
) -> tuple[list[sqlite3.Row], int]:
    """Bounded list and matching count from one read snapshot; no session hydration."""
    if (
        ai_filter not in {"all", "with-ai", "without-ai"}
        or not 1 <= limit <= 100 or not 0 <= offset <= 1_000_000 or len(q) > 500
    ):
        raise ValueError("Invalid history query")
    exists = "EXISTS(SELECT 1 FROM ai_sessions a WHERE a.divination_id = d.id)"
    clauses = []
    parameters: list[Any] = []
    if q.strip():
        # Literal substring semantics: %, _ and backslash are not wildcards.
        escaped = q.strip().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        clauses.append("d.question LIKE ? ESCAPE '\\'")
        parameters.append(f"%{escaped}%")
    if ai_filter != "all":
        clauses.append(exists if ai_filter == "with-ai" else f"NOT {exists}")
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    db = connect(db_path)
    try:
        db.execute("BEGIN")
        total = db.execute(f"SELECT COUNT(*) FROM divinations d {where}", parameters).fetchone()[0]
        rows = db.execute(
            f"""SELECT d.id, d.question, d.method, d.result_json, d.created_at,
                {exists} AS has_ai_sessions FROM divinations d {where}
                ORDER BY d.created_at DESC, d.id DESC LIMIT ? OFFSET ?""",
            [*parameters, limit, offset],
        ).fetchall()
        return rows, total
    finally:
        db.close()


def get(db_path: Path, record_id: int) -> sqlite3.Row | None:
    db = connect(db_path)
    try:
        return db.execute("SELECT * FROM divinations WHERE id = ?", (record_id,)).fetchone()
    finally:
        db.close()


def delete(db_path: Path, record_id: int) -> bool:
    db = connect(db_path)
    try:
        cursor = db.execute("DELETE FROM divinations WHERE id = ?", (record_id,))
        db.commit()
        return cursor.rowcount > 0
    finally:
        db.close()


def save_najia_context(
    db_path: Path,
    record_id: int,
    chart: dict[str, Any],
    params: dict[str, Any],
    updated_at: str,
    calendar_context: dict[str, Any] | None = None,
) -> None:
    db = connect(db_path)
    try:
        cursor = db.execute("SELECT 1 FROM divinations WHERE id = ?", (record_id,))
        if cursor.fetchone() is None:
            raise KeyError(record_id)
        db.execute(
            """INSERT INTO divination_context(
                divination_id, najia_json, najia_params_json, calendar_context_json, updated_at
            ) VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(divination_id) DO UPDATE SET
                najia_json=excluded.najia_json,
                najia_params_json=excluded.najia_params_json,
                calendar_context_json=excluded.calendar_context_json,
                updated_at=excluded.updated_at""",
            (
                record_id,
                json.dumps(chart, ensure_ascii=False),
                json.dumps(params, ensure_ascii=False),
                json.dumps(calendar_context, ensure_ascii=False) if calendar_context is not None else None,
                updated_at,
            ),
        )
        db.commit()
    finally:
        db.close()


def get_divination_context(db_path: Path, record_id: int) -> dict[str, Any] | None:
    db = connect(db_path)
    try:
        row = db.execute("SELECT * FROM divination_context WHERE divination_id = ?", (record_id,)).fetchone()
        if row is None:
            return None
        return {
            "reading": json.loads(row["reading_json"]) if row["reading_json"] else None,
            "ruleset_id": row["ruleset_id"],
            "ruleset_version": row["ruleset_version"],
            "najia_chart": json.loads(row["najia_json"]) if row["najia_json"] else None,
            "najia_params": json.loads(row["najia_params_json"]) if row["najia_params_json"] else None,
            "calendar_context": json.loads(row["calendar_context_json"]) if row["calendar_context_json"] else None,
            "updated_at": row["updated_at"],
        }
    finally:
        db.close()


def get_setting(db_path: Path, key: str) -> Any | None:
    db = connect(db_path)
    try:
        row = db.execute("SELECT value_json FROM app_settings WHERE key = ?", (key,)).fetchone()
        return json.loads(row["value_json"]) if row else None
    finally:
        db.close()


def save_setting(db_path: Path, key: str, value: Any, updated_at: str) -> None:
    db = connect(db_path)
    try:
        db.execute(
            """INSERT INTO app_settings(key, value_json, updated_at) VALUES (?, ?, ?)
            ON CONFLICT(key) DO UPDATE SET value_json=excluded.value_json, updated_at=excluded.updated_at""",
            (key, json.dumps(value, ensure_ascii=False), updated_at),
        )
        db.commit()
    finally:
        db.close()


def delete_setting(db_path: Path, key: str) -> None:
    db = connect(db_path)
    try:
        db.execute("DELETE FROM app_settings WHERE key = ?", (key,))
        db.commit()
    finally:
        db.close()


def create_ai_session(
    db_path: Path, divination_id: int, mode: str, model_id: str, context: dict[str, Any], created_at: str
) -> int:
    db = connect(db_path)
    try:
        cursor = db.execute(
            "INSERT INTO ai_sessions(divination_id, mode, model_id, context_json, created_at) VALUES (?, ?, ?, ?, ?)",
            (divination_id, mode, model_id, json.dumps(context, ensure_ascii=False), created_at),
        )
        db.commit()
        return int(cursor.lastrowid)
    finally:
        db.close()


def list_ai_sessions(db_path: Path, divination_id: int) -> list[dict[str, Any]]:
    db = connect(db_path)
    try:
        rows = db.execute(
            "SELECT id, mode, model_id, context_json, created_at FROM ai_sessions WHERE divination_id = ? ORDER BY id",
            (divination_id,),
        ).fetchall()
        return [
            {"id": row["id"], "mode": row["mode"], "model_id": row["model_id"],
             "rule_versions": json.loads(row["context_json"]).get("rule_versions", {}), "created_at": row["created_at"]}
            for row in rows
        ]
    finally:
        db.close()


def get_ai_session(db_path: Path, session_id: int) -> dict[str, Any] | None:
    db = connect(db_path)
    try:
        row = db.execute("SELECT * FROM ai_sessions WHERE id = ?", (session_id,)).fetchone()
        if row is None:
            return None
        return {
            "id": row["id"],
            "divination_id": row["divination_id"],
            "mode": row["mode"],
            "model_id": row["model_id"],
            "context": json.loads(row["context_json"]),
            "rule_versions": json.loads(row["context_json"]).get("rule_versions", {}),
            "created_at": row["created_at"],
        }
    finally:
        db.close()


def list_ai_messages(db_path: Path, session_id: int) -> list[dict[str, Any]]:
    db = connect(db_path)
    try:
        rows = db.execute(
            """SELECT m.id, m.role, m.content_json, m.created_at,
                      r.request_id, r.user_message_id
               FROM ai_messages m
               LEFT JOIN ai_requests r ON r.assistant_message_id = m.id
               WHERE m.session_id = ? ORDER BY m.id""",
            (session_id,),
        ).fetchall()
        return [
            {
                "id": row["id"], "role": row["role"],
                "content": json.loads(row["content_json"]), "created_at": row["created_at"],
                "request_id": row["request_id"], "user_message_id": row["user_message_id"],
            }
            for row in rows
        ]
    finally:
        db.close()


def list_ai_request_failures(db_path: Path, session_id: int) -> list[dict[str, Any]]:
    db = connect(db_path)
    try:
        rows = db.execute(
            """SELECT request_id, message_text, regenerate_from_message_id,
                      code, stage, public_message, created_at
               FROM ai_request_failures WHERE session_id = ? ORDER BY id""",
            (session_id,),
        ).fetchall()
        return [
            {
                "request_id": row["request_id"],
                "message_text": row["message_text"],
                "regenerate_from_message_id": row["regenerate_from_message_id"],
                "code": row["code"],
                "stage": row["stage"],
                "message": row["public_message"],
                "created_at": row["created_at"],
            }
            for row in rows
        ]
    finally:
        db.close()


def find_ai_request_failure(db_path: Path, session_id: int, request_id: str) -> dict[str, Any] | None:
    db = connect(db_path)
    try:
        row = db.execute(
            """SELECT request_id, message_text, regenerate_from_message_id
               FROM ai_request_failures WHERE session_id = ? AND request_id = ?""",
            (session_id, request_id),
        ).fetchone()
        return dict(row) if row is not None else None
    finally:
        db.close()


def save_ai_request_failure(
    db_path: Path,
    *,
    session_id: int,
    request_id: str,
    message_text: str,
    regenerate_from_message_id: int | None,
    code: str,
    stage: str,
    public_message: str,
    created_at: str,
) -> bool:
    """Persist only a failed request's user-visible status, never model output."""
    db = connect(db_path)
    try:
        db.execute("BEGIN IMMEDIATE")
        completed = db.execute(
            "SELECT message_text, regenerate_from_message_id FROM ai_requests WHERE session_id = ? AND request_id = ?",
            (session_id, request_id),
        ).fetchone()
        if completed is not None:
            # A dropped SSE connection can race with an already committed answer.
            # The durable success is authoritative and must not be marked failed.
            db.execute(
                "DELETE FROM ai_request_failures WHERE session_id = ? AND request_id = ?",
                (session_id, request_id),
            )
            db.commit()
            return False

        existing = db.execute(
            "SELECT message_text, regenerate_from_message_id FROM ai_request_failures WHERE session_id = ? AND request_id = ?",
            (session_id, request_id),
        ).fetchone()
        if existing is not None and (
            existing["message_text"] != message_text
            or existing["regenerate_from_message_id"] != regenerate_from_message_id
        ):
            raise ValueError("请求编号已用于另一条失败请求")

        db.execute(
            """INSERT INTO ai_request_failures(
                   session_id, request_id, message_text, regenerate_from_message_id,
                   code, stage, public_message, created_at
               ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(session_id, request_id) DO UPDATE SET
                   code = excluded.code,
                   stage = excluded.stage,
                   public_message = excluded.public_message,
                   created_at = excluded.created_at""",
            (
                session_id,
                request_id,
                message_text,
                regenerate_from_message_id,
                code,
                stage,
                public_message,
                created_at,
            ),
        )
        db.commit()
        return True
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def add_ai_message(db_path: Path, session_id: int, role: str, content: Any, created_at: str) -> int:
    db = connect(db_path)
    try:
        cursor = db.execute(
            "INSERT INTO ai_messages(session_id, role, content_json, created_at) VALUES (?, ?, ?, ?)",
            (session_id, role, json.dumps(content, ensure_ascii=False), created_at),
        )
        db.commit()
        return int(cursor.lastrowid)
    finally:
        db.close()


def find_ai_request(db_path: Path, session_id: int, request_id: str) -> dict[str, Any] | None:
    db = connect(db_path)
    try:
        row = db.execute(
            """SELECT r.request_id, r.message_text, r.regenerate_from_message_id,
                      r.user_message_id, r.assistant_message_id, m.content_json, m.created_at
               FROM ai_requests r JOIN ai_messages m ON m.id = r.assistant_message_id
               WHERE r.session_id = ? AND r.request_id = ?""",
            (session_id, request_id),
        ).fetchone()
        if row is None:
            return None
        return {
            "request_id": row["request_id"],
            "message_text": row["message_text"],
            "regenerate_from_message_id": row["regenerate_from_message_id"],
            "user_message_id": row["user_message_id"],
            "assistant_message_id": row["assistant_message_id"],
            "assistant_message": {
                "id": row["assistant_message_id"], "role": "assistant",
                "content": json.loads(row["content_json"]), "created_at": row["created_at"],
            },
        }
    finally:
        db.close()


def save_ai_exchange(
    db_path: Path,
    *,
    session_id: int,
    request_id: str,
    message_text: str,
    assistant_content: dict[str, Any],
    created_at: str,
    regenerate_from_message_id: int | None = None,
) -> dict[str, Any]:
    """Atomically store a completed exchange, or only its regenerated answer."""
    db = connect(db_path)
    try:
        db.execute("BEGIN IMMEDIATE")
        existing = db.execute(
            "SELECT message_text, regenerate_from_message_id, assistant_message_id FROM ai_requests WHERE session_id = ? AND request_id = ?",
            (session_id, request_id),
        ).fetchone()
        if existing:
            if existing["message_text"] != message_text or existing["regenerate_from_message_id"] != regenerate_from_message_id:
                raise ValueError("请求编号已用于另一条消息")
            db.execute(
                "DELETE FROM ai_request_failures WHERE session_id = ? AND request_id = ?",
                (session_id, request_id),
            )
            db.commit()
            replay = find_ai_request(db_path, session_id, request_id)
            if replay is None:
                raise RuntimeError("已保存的 AI 请求结果无法读取")
            return replay

        failed = db.execute(
            "SELECT message_text, regenerate_from_message_id FROM ai_request_failures WHERE session_id = ? AND request_id = ?",
            (session_id, request_id),
        ).fetchone()
        if failed is not None and (
            failed["message_text"] != message_text
            or failed["regenerate_from_message_id"] != regenerate_from_message_id
        ):
            raise ValueError("请求编号已用于另一条消息")

        user_message_id: int | None
        if regenerate_from_message_id is None:
            cursor = db.execute(
                "INSERT INTO ai_messages(session_id, role, content_json, created_at) VALUES (?, 'user', ?, ?)",
                (session_id, json.dumps(message_text, ensure_ascii=False), created_at),
            )
            user_message_id = int(cursor.lastrowid)
        else:
            target = db.execute(
                "SELECT role, content_json FROM ai_messages WHERE id = ? AND session_id = ?",
                (regenerate_from_message_id, session_id),
            ).fetchone()
            last_user = db.execute(
                "SELECT id FROM ai_messages WHERE session_id = ? AND role = 'user' ORDER BY id DESC LIMIT 1",
                (session_id,),
            ).fetchone()
            if target is None or target["role"] != "user" or last_user is None or last_user["id"] != regenerate_from_message_id:
                raise ValueError("只能重新生成当前会话最后一条用户消息的回答")
            if json.loads(target["content_json"]) != message_text:
                raise ValueError("重新生成的消息内容与原消息不一致")
            user_message_id = regenerate_from_message_id

        assistant_cursor = db.execute(
            "INSERT INTO ai_messages(session_id, role, content_json, created_at) VALUES (?, 'assistant', ?, ?)",
            (session_id, json.dumps(assistant_content, ensure_ascii=False), created_at),
        )
        assistant_message_id = int(assistant_cursor.lastrowid)
        db.execute(
            """INSERT INTO ai_requests(
                session_id, request_id, message_text, regenerate_from_message_id,
                user_message_id, assistant_message_id, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (session_id, request_id, message_text, regenerate_from_message_id, user_message_id,
             assistant_message_id, created_at),
        )
        db.execute(
            "DELETE FROM ai_request_failures WHERE session_id = ? AND request_id = ?",
            (session_id, request_id),
        )
        db.commit()
        return {
            "request_id": request_id,
            "message_text": message_text,
            "regenerate_from_message_id": regenerate_from_message_id,
            "user_message_id": user_message_id,
            "assistant_message_id": assistant_message_id,
            "assistant_message": {
                "id": assistant_message_id, "role": "assistant", "content": assistant_content,
                "created_at": created_at,
            },
        }
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
