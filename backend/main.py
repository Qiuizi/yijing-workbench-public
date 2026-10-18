"""FastAPI application for the local I Ching divination workbench."""

from __future__ import annotations

import json
import os
import asyncio
import hmac
import logging
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from fastapi import FastAPI, HTTPException, Query, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse

from backend.catalog import HexagramCatalog, load_catalog
from backend.core.casting import cast_six_lines
from backend.core.hexagram import calculate_hexagram
from backend.core.najia import EARTHLY_BRANCHES, SEXAGENARY_CYCLE, build_najia_chart
from backend.core.najia_analysis import analyze_najia_chart
from backend.core.reading_rules import choose_traditional_reading, reading_as_dict
from backend.models import (
    DivinationRequest,
    DivinationResponse,
    ErrorResponse,
    AIMessageRequest,
    AISettingsUpdate,
    AISessionCreate,
    HexagramResponse,
    HexagramSummaryResponse,
    HistoryListResponse,
    ManualDivinationRequest,
    NajiaChartResponse,
    NajiaRequest,
    PreferencesUpdate,
)
from backend.services import history
from backend.services import ai_secrets
from backend.services.calendar import CalendarInputError, calculate_calendar_inputs, load_iana_timezone
from backend.services.ai_provider import AIProvider, AIProviderError, AIStreamChunk, DeepSeekProvider
from backend.services.ai_cost import estimate_cost
from backend.services.ai_runtime import AIOutputValidationError, build_ai_context, build_chat_messages, validate_ai_output
from backend.services.desktop_migration import DesktopMigrationError, import_legacy_database, migration_status


ai_logger = logging.getLogger("backend.ai")


def _default_db_path() -> Path:
    configured = os.environ.get("YIJING_DB_PATH")
    return Path(configured).expanduser() if configured else Path(__file__).parent / "data" / "history.sqlite3"


def _hexagram_response(entry: dict[str, Any]) -> dict[str, Any]:
    return entry


def _build_result(
    *, question: str, method: str, lines: tuple[int, ...], coin_faces: tuple[tuple[int, int, int], ...] | None,
    catalog: HexagramCatalog,
) -> dict[str, Any]:
    calculation = calculate_hexagram(lines, catalog.by_code)
    base = catalog.by_id[calculation.base_id]
    changed = catalog.by_id[calculation.changed_id]
    traditional_reading = reading_as_dict(choose_traditional_reading(calculation, base, changed))
    result_lines = []
    for index, value in enumerate(lines):
        result_lines.append(
            {
                "position": index + 1,
                "value": value,
                "yin_yang": "阳" if value in (7, 9) else "阴",
                "changing": value in (6, 9),
                "coins": list(coin_faces[index]) if coin_faces is not None else None,
            }
        )
    changed_lines = [
        {
            "position": index + 1,
            "value": value,
            "yin_yang": "阳" if value in (7, 9) else "阴",
            "changing": lines[index] in (6, 9),
            "coins": None,
        }
        for index, value in enumerate(calculation.changed_lines)
    ]
    return {
        "question": question,
        "method": method,
        "lines": result_lines,
        "changed_lines": changed_lines,
        "moving_positions": list(calculation.moving_positions),
        "base_hexagram": _hexagram_response(base),
        "changed_hexagram": _hexagram_response(changed),
        "traditional_reading": traditional_reading,
    }


def create_app(
    db_path: Path | None = None,
    catalog: HexagramCatalog | None = None,
    ai_provider: AIProvider | None = None,
    secret_store: Any | None = None,
    desktop_mode: bool | None = None,
    desktop_api_token: str | None = None,
    desktop_dev_mode: bool | None = None,
) -> FastAPI:
    actual_db_path = Path(db_path) if db_path is not None else _default_db_path()
    actual_catalog = catalog if catalog is not None else load_catalog()
    is_desktop = desktop_mode if desktop_mode is not None else os.environ.get("YIJING_DESKTOP_MODE") == "1"
    is_desktop_dev = desktop_dev_mode if desktop_dev_mode is not None else os.environ.get("YIJING_DESKTOP_DEV") == "1"
    api_token = desktop_api_token if desktop_api_token is not None else os.environ.get("YIJING_API_TOKEN")
    if is_desktop and not api_token:
        raise ValueError("桌面模式必须配置运行时 API 鉴权令牌")

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        history.initialize(actual_db_path)
        yield

    app = FastAPI(
        title="易经起卦工作台",
        version="3.3.0",
        description="本地起卦、卦象资料与历史记录 API",
        lifespan=lifespan,
    )
    app.state.db_path = actual_db_path
    app.state.catalog = actual_catalog
    app.state.ai_provider = ai_provider or DeepSeekProvider()
    app.state.secret_store = secret_store or ai_secrets
    app.state.desktop_mode = is_desktop
    app.state.desktop_allowed_origins = ["http://tauri.localhost", "https://tauri.localhost", "tauri://localhost"]
    if is_desktop and is_desktop_dev:
        app.state.desktop_allowed_origins.append("http://127.0.0.1:5174")
    app.state.desktop_api_token = api_token
    app.state.desktop_backup_dir = Path(os.environ.get("YIJING_BACKUP_DIR", actual_db_path.parent / "backups"))
    app.state.ai_request_locks = {}
    app.state.ai_request_lock_guard = asyncio.Lock()
    app.add_middleware(
        CORSMiddleware,
        allow_origins=(
            app.state.desktop_allowed_origins
            if is_desktop else ["http://localhost:5173", "http://127.0.0.1:5173"]
        ),
        allow_methods=["GET", "POST", "PUT", "DELETE"],
        allow_headers=["Content-Type", "Authorization"],
    )

    @app.middleware("http")
    async def desktop_api_guard(request: Request, call_next):
        if is_desktop:
            origin = request.headers.get("origin")
            allowed_origins = set(request.app.state.desktop_allowed_origins)
            if origin is not None and origin not in allowed_origins:
                return JSONResponse(status_code=403, content={"error": {"code": "ORIGIN_DENIED", "message": "桌面应用来源未获授权"}})
            if request.url.path.startswith("/api/") and request.method != "OPTIONS":
                authorization = request.headers.get("authorization", "")
                expected = f"Bearer {api_token}"
                if not hmac.compare_digest(authorization, expected):
                    return JSONResponse(status_code=401, content={"error": {"code": "UNAUTHORIZED", "message": "本地 API 鉴权失败"}})
        return await call_next(request)

    @app.exception_handler(HTTPException)
    async def http_error_handler(_: Request, exc: HTTPException) -> JSONResponse:
        code = "NOT_FOUND" if exc.status_code == 404 else "REQUEST_ERROR"
        message = str(exc.detail)
        return JSONResponse(status_code=exc.status_code, content={"error": {"code": code, "message": message}})

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content={
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "请求参数无效",
                    "details": [
                        {"loc": list(error["loc"]), "msg": str(error["msg"]), "type": error["type"]}
                        for error in exc.errors()
                    ],
                }
            },
        )

    @app.get("/api/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/api/desktop/health")
    async def desktop_health(request: Request) -> dict[str, str]:
        if not request.app.state.desktop_mode:
            raise HTTPException(status_code=404, detail="未启用桌面运行模式")
        return {"status": "ok", "mode": "desktop"}

    @app.get("/api/desktop/migration/status")
    async def desktop_migration_status(request: Request) -> dict[str, Any]:
        if not request.app.state.desktop_mode:
            raise HTTPException(status_code=404, detail="未启用桌面运行模式")
        return migration_status(request.app.state.db_path)

    @app.post("/api/desktop/migration/import")
    async def desktop_import_legacy(data: dict[str, str], request: Request) -> dict[str, Any]:
        if not request.app.state.desktop_mode:
            raise HTTPException(status_code=404, detail="未启用桌面运行模式")
        source_path = data.get("source_path", "").strip()
        if not source_path or len(source_path) > 32768:
            raise HTTPException(status_code=422, detail="请选择有效的旧版 SQLite 数据库文件")
        try:
            return import_legacy_database(
                request.app.state.db_path,
                Path(source_path),
                request.app.state.desktop_backup_dir,
                request.app.state.secret_store,
            )
        except DesktopMigrationError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    @app.get("/api/preferences")
    async def get_preferences() -> dict[str, Any]:
        saved = history.get_setting(actual_db_path, "app_preferences") or {}
        return {
            "default_method": saved.get("default_method", "coins"),
            "timezone": saved.get("timezone", "Asia/Shanghai"),
            "ai_default_mode": saved.get("ai_default_mode", "classical"),
            "ruleset_id": "qiming-tongshi",
            "ruleset_version": "1.0.0",
        }

    @app.put("/api/preferences")
    async def update_preferences(data: PreferencesUpdate) -> dict[str, Any]:
        saved = history.get_setting(actual_db_path, "app_preferences") or {}
        timezone_name = data.timezone or saved.get("timezone", "Asia/Shanghai")
        try:
            load_iana_timezone(timezone_name)
        except CalendarInputError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        history.save_setting(
            actual_db_path,
            "app_preferences",
            {
                "default_method": data.default_method,
                "timezone": timezone_name,
                "ai_default_mode": data.ai_default_mode or saved.get("ai_default_mode", "classical"),
            },
            datetime.now(timezone.utc).isoformat(),
        )
        return await get_preferences()

    def ai_public_settings() -> dict[str, Any]:
        settings = history.get_setting(actual_db_path, "ai_public_settings") or {}
        protected_key = history.get_setting(actual_db_path, "deepseek_api_key_protected")
        try:
            configured = bool(app.state.secret_store.unprotect(protected_key))
        except Exception:
            configured = False
        return {
            "provider": "deepseek",
            "api_key_configured": configured,
            "ai_enabled": bool(settings.get("ai_enabled", False)) and configured,
            "model_id": settings.get("model_id"),
        }

    def load_api_key() -> str | None:
        protected_key = history.get_setting(actual_db_path, "deepseek_api_key_protected")
        try:
            return app.state.secret_store.unprotect(protected_key)
        except Exception as exc:
            raise HTTPException(status_code=503, detail="无法解密本机 API Key，请重新录入") from exc

    @app.get("/api/ai/settings")
    async def get_ai_settings() -> dict[str, Any]:
        return ai_public_settings()

    @app.put("/api/ai/settings")
    async def update_ai_settings(data: AISettingsUpdate) -> dict[str, Any]:
        settings = history.get_setting(actual_db_path, "ai_public_settings") or {}
        current_key = load_api_key()
        candidate_key = data.api_key.strip() if data.api_key is not None else current_key
        if data.api_key is not None and not candidate_key:
            raise HTTPException(status_code=422, detail="API Key 不能为空")
        if data.api_key is not None:
            settings["model_id"] = None
            settings["ai_enabled"] = False
        if data.model_id is not None:
            if not candidate_key:
                raise HTTPException(status_code=409, detail="请先配置 DeepSeek API Key")
            try:
                models = await app.state.ai_provider.list_models(candidate_key)
            except AIProviderError as exc:
                raise HTTPException(status_code=502, detail=str(exc)) from exc
            if data.model_id not in {model["id"] for model in models}:
                raise HTTPException(status_code=422, detail="所选模型不在 DeepSeek 当前可用模型列表中，请刷新模型列表")
            settings["model_id"] = data.model_id
        if data.ai_enabled is not None:
            if data.ai_enabled and (not candidate_key or not settings.get("model_id")):
                raise HTTPException(status_code=409, detail="启用 AI 前请先录入 API Key 并选择可用模型")
            settings["ai_enabled"] = data.ai_enabled
        updated_at = datetime.now(timezone.utc).isoformat()
        protected = None
        if data.api_key is not None:
            try:
                protected = app.state.secret_store.protect(candidate_key)
            except Exception as exc:
                raise HTTPException(status_code=503, detail="本机无法安全保存 API Key") from exc
            history.save_setting(actual_db_path, "deepseek_api_key_protected", protected, updated_at)
        history.save_setting(actual_db_path, "ai_public_settings", settings, updated_at)
        return ai_public_settings()

    @app.delete("/api/ai/settings/key", status_code=204)
    async def delete_ai_key() -> Response:
        history.delete_setting(actual_db_path, "deepseek_api_key_protected")
        settings = history.get_setting(actual_db_path, "ai_public_settings") or {}
        settings.update({"ai_enabled": False, "model_id": None})
        history.save_setting(actual_db_path, "ai_public_settings", settings, datetime.now(timezone.utc).isoformat())
        return Response(status_code=204)

    @app.get("/api/ai/models")
    async def list_ai_models() -> dict[str, Any]:
        api_key = load_api_key()
        if not api_key:
            raise HTTPException(status_code=409, detail="请先配置 DeepSeek API Key")
        try:
            models = await app.state.ai_provider.list_models(api_key)
        except AIProviderError as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc
        return {"models": models}

    @app.post("/api/ai/test-connection")
    async def test_ai_connection() -> dict[str, Any]:
        api_key = load_api_key()
        if not api_key:
            raise HTTPException(status_code=409, detail="请先配置 DeepSeek API Key")
        try:
            models = await app.state.ai_provider.list_models(api_key)
        except AIProviderError as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc
        return {"ok": True, "provider": "deepseek", "available_models": len(models)}

    @app.get("/api/najia/options")
    async def najia_options() -> dict[str, list[str]]:
        return {"day_ganzhi_options": list(SEXAGENARY_CYCLE), "month_branches": list(EARTHLY_BRANCHES)}

    @app.get("/api/hexagrams", response_model=list[HexagramSummaryResponse])
    async def list_hexagrams(request: Request) -> list[dict[str, Any]]:
        return sorted(request.app.state.catalog.entries, key=lambda entry: entry["wenwang_order"])

    @app.get("/api/hexagrams/{hexagram_id}", response_model=HexagramResponse, responses={404: {"model": ErrorResponse}})
    async def get_hexagram(hexagram_id: int, request: Request) -> dict[str, Any]:
        if not 1 <= hexagram_id <= 64:
            raise HTTPException(status_code=404, detail="未找到该卦象")
        entry = request.app.state.catalog.get(hexagram_id)
        if entry is None:
            raise HTTPException(status_code=404, detail="未找到该卦象")
        return entry

    @app.post("/api/divination", response_model=DivinationResponse, responses={422: {"model": ErrorResponse}})
    async def divine(request_data: DivinationRequest, request: Request) -> dict[str, Any]:
        cast = cast_six_lines()
        result = _build_result(
            question=request_data.question,
            method="coins",
            lines=tuple(line.value for line in cast),
            coin_faces=tuple(line.coins for line in cast),
            catalog=request.app.state.catalog,
        )
        created_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
        record_id = history.create(request.app.state.db_path, result, created_at)
        return {**result, "id": record_id, "created_at": created_at}

    @app.post("/api/divination/manual", response_model=DivinationResponse, responses={422: {"model": ErrorResponse}})
    async def divine_manual(request_data: ManualDivinationRequest, request: Request) -> dict[str, Any]:
        result = _build_result(
            question=request_data.question,
            method="manual",
            lines=tuple(request_data.lines),
            coin_faces=None,
            catalog=request.app.state.catalog,
        )
        created_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
        record_id = history.create(request.app.state.db_path, result, created_at)
        return {**result, "id": record_id, "created_at": created_at}

    @app.get("/api/history", response_model=HistoryListResponse)
    async def list_history(
        request: Request,
        q: str = Query(default="", max_length=500),
        ai_filter: Literal["all", "with-ai", "without-ai"] = Query(default="all"),
        limit: int = Query(default=20, ge=1, le=100),
        offset: int = Query(default=0, ge=0, le=1_000_000),
    ) -> dict[str, Any]:
        rows, total = history.list_page(request.app.state.db_path, q=q, ai_filter=ai_filter, limit=limit, offset=offset)
        items = []
        for row in rows:
            result = json.loads(row["result_json"])
            items.append(
                {
                    "id": row["id"],
                    "question": row["question"],
                    "method": row["method"],
                    "base_name": result["base_hexagram"]["title"],
                    "changed_name": result["changed_hexagram"]["title"],
                    "moving_positions": result["moving_positions"],
                    "created_at": row["created_at"],
                    "has_ai_sessions": bool(row["has_ai_sessions"]),
                }
            )
        return {"items": items, "total": total}

    @app.get("/api/history/{record_id}", response_model=DivinationResponse, responses={404: {"model": ErrorResponse}})
    async def get_history(record_id: int, request: Request) -> dict[str, Any]:
        row = history.get(request.app.state.db_path, record_id)
        if row is None:
            raise HTTPException(status_code=404, detail="未找到这条历史记录")
        result = json.loads(row["result_json"])
        context = history.get_divination_context(request.app.state.db_path, record_id)
        if context:
            result.setdefault("traditional_reading", context.get("reading"))
            result["najia_chart"] = context.get("najia_chart")
        result["ai_sessions"] = history.list_ai_sessions(request.app.state.db_path, record_id)
        if not result.get("traditional_reading") and len(result.get("lines", [])) == 6:
            try:
                line_values = tuple(line["value"] for line in result["lines"])
                calculation = calculate_hexagram(line_values, request.app.state.catalog.by_code)
                base = dict(result["base_hexagram"])
                changed = dict(result["changed_hexagram"])
                for entry in (base, changed):
                    catalog_entry = request.app.state.catalog.by_id.get(entry.get("wenwang_order"))
                    if catalog_entry and not entry.get("special_line"):
                        entry["special_line"] = catalog_entry.get("special_line")
                result["traditional_reading"] = reading_as_dict(
                    choose_traditional_reading(calculation, base, changed)
                )
            except (KeyError, ValueError, TypeError):
                # Keep malformed or partial legacy rows readable without V2 enrichment.
                pass
        return {**result, "id": row["id"], "created_at": row["created_at"]}

    @app.post(
        "/api/history/{record_id}/najia",
        response_model=NajiaChartResponse,
        responses={404: {"model": ErrorResponse}, 422: {"model": ErrorResponse}},
    )
    async def create_najia_chart(record_id: int, request_data: NajiaRequest, request: Request) -> dict[str, Any]:
        row = history.get(request.app.state.db_path, record_id)
        if row is None:
            raise HTTPException(status_code=404, detail="未找到这条历史记录")
        result = json.loads(row["result_json"])
        stored_lines = result.get("lines")
        if not isinstance(stored_lines, list) or len(stored_lines) != 6:
            raise HTTPException(status_code=422, detail="这条旧记录没有完整六爻，无法排盘")
        try:
            calendar = None
            if request_data.source == "automatic":
                calendar = calculate_calendar_inputs(request_data.local_datetime or "", request_data.timezone or "")
                day_ganzhi = calendar.day_ganzhi
                month_branch = calendar.month_branch
            else:
                day_ganzhi = request_data.day_ganzhi or ""
                month_branch = request_data.month_branch or ""
            values = tuple(line["value"] for line in stored_lines)
            calculation = calculate_hexagram(values, request.app.state.catalog.by_code)
            chart = build_najia_chart(
                calculation=calculation,
                base_hexagram=request.app.state.catalog.by_id[calculation.base_id],
                changed_hexagram=request.app.state.catalog.by_id[calculation.changed_id],
                day_ganzhi=day_ganzhi,
                month_branch=month_branch,
                catalog=request.app.state.catalog,
                timestamp_source=request_data.source,
            )
            chart["calendar_context"] = calendar.context if calendar else None
            chart["rule_analysis"] = analyze_najia_chart(
                chart,
                enabled=request_data.analysis.enabled.model_dump(),
                question_category=request_data.analysis.question_category,
                manual_use_god_candidate=request_data.analysis.manual_use_god_candidate,
            )
        except (CalendarInputError, ValueError, KeyError, TypeError) as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        params = (
            {"source": "automatic", "local_datetime": request_data.local_datetime, "timezone": request_data.timezone}
            if request_data.source == "automatic"
            else {"source": "manual", "day_ganzhi": day_ganzhi, "month_branch": month_branch}
        )
        params["analysis"] = request_data.analysis.model_dump(mode="json")
        history.save_najia_context(
            request.app.state.db_path,
            record_id,
            chart,
            params,
            datetime.now(timezone.utc).isoformat(timespec="seconds"),
            calendar.context if calendar else None,
        )
        return chart

    def stored_divination(record_id: int) -> dict[str, Any]:
        row = history.get(actual_db_path, record_id)
        if row is None:
            raise HTTPException(status_code=404, detail="未找到这条起卦记录")
        result = json.loads(row["result_json"])
        context = history.get_divination_context(actual_db_path, record_id)
        if context:
            result.setdefault("traditional_reading", context.get("reading"))
            if context.get("najia_chart"):
                result["najia_chart"] = context["najia_chart"]
        if not result.get("traditional_reading") and len(result.get("lines", [])) == 6:
            try:
                values = tuple(line["value"] for line in result["lines"])
                calculation = calculate_hexagram(values, actual_catalog.by_code)
                base = actual_catalog.by_id[calculation.base_id]
                changed = actual_catalog.by_id[calculation.changed_id]
                result["traditional_reading"] = reading_as_dict(choose_traditional_reading(calculation, base, changed))
            except (KeyError, ValueError, TypeError):
                pass
        result["id"] = row["id"]
        result["created_at"] = row["created_at"]
        return result

    @app.post("/api/ai/sessions")
    async def create_ai_session(data: AISessionCreate) -> dict[str, Any]:
        settings = ai_public_settings()
        api_key = load_api_key()
        if not settings["ai_enabled"]:
            raise HTTPException(status_code=409, detail="请先在设置中配置并启用 AI")
        if not api_key or not settings["model_id"]:
            raise HTTPException(status_code=409, detail="AI 配置不完整，请检查 API Key 与模型")
        result = stored_divination(data.divination_id)
        try:
            context = build_ai_context(result, data.mode)
        except (ValueError, KeyError, TypeError) as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        created_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
        session_id = history.create_ai_session(
            actual_db_path, data.divination_id, data.mode, settings["model_id"], context, created_at
        )
        return {"id": session_id, "divination_id": data.divination_id, "mode": data.mode,
                "model_id": settings["model_id"], "rule_versions": context.get("rule_versions", {}),
                "created_at": created_at, "messages": []}

    @app.get("/api/history/{record_id}/ai-sessions")
    async def get_ai_sessions(record_id: int) -> dict[str, Any]:
        if history.get(actual_db_path, record_id) is None:
            raise HTTPException(status_code=404, detail="未找到这条起卦记录")
        return {"items": history.list_ai_sessions(actual_db_path, record_id)}

    @app.get("/api/ai/sessions/{session_id}")
    async def get_ai_session(session_id: int) -> dict[str, Any]:
        session = history.get_ai_session(actual_db_path, session_id)
        if session is None:
            raise HTTPException(status_code=404, detail="未找到这条 AI 会话")
        return {key: value for key, value in session.items() if key != "context"} | {
            "messages": history.list_ai_messages(actual_db_path, session_id),
            "failed_requests": history.list_ai_request_failures(actual_db_path, session_id),
        }

    async def acquire_ai_request_lock(key: tuple[int, str]) -> dict[str, Any]:
        async with app.state.ai_request_lock_guard:
            lock_state = app.state.ai_request_locks.get(key)
            if lock_state is None:
                lock_state = {"lock": asyncio.Lock(), "users": 0}
                app.state.ai_request_locks[key] = lock_state
            lock_state["users"] += 1
        try:
            await lock_state["lock"].acquire()
        except asyncio.CancelledError:
            async with app.state.ai_request_lock_guard:
                lock_state["users"] -= 1
                if lock_state["users"] == 0:
                    app.state.ai_request_locks.pop(key, None)
            raise
        return lock_state

    async def release_ai_request_lock(key: tuple[int, str], lock_state: dict[str, Any]) -> None:
        lock_state["lock"].release()
        async with app.state.ai_request_lock_guard:
            lock_state["users"] -= 1
            if lock_state["users"] == 0:
                app.state.ai_request_locks.pop(key, None)

    @app.post("/api/ai/sessions/{session_id}/messages")
    async def add_ai_message(session_id: int, data: AIMessageRequest) -> StreamingResponse:
        session = history.get_ai_session(actual_db_path, session_id)
        if session is None:
            raise HTTPException(status_code=404, detail="未找到这条 AI 会话")

        def event(name: str, payload: Any) -> str:
            return f"event: {name}\ndata: {json.dumps(payload, ensure_ascii=False, separators=(',', ':'))}\n\n"

        def completed_payload(saved: dict[str, Any], user_text: str) -> dict[str, Any]:
            assistant = saved["assistant_message"]
            return {
                "message": assistant,
                "user_message": {
                    "id": saved["user_message_id"],
                    "role": "user",
                    "content": user_text,
                    "created_at": assistant["created_at"],
                },
            }

        cached = history.find_ai_request(actual_db_path, session_id, str(data.request_id))
        if cached:
            if cached["message_text"] != data.message or cached["regenerate_from_message_id"] != data.regenerate_from_message_id:
                raise HTTPException(status_code=409, detail="请求编号已用于另一条消息")

            async def replay_response():
                yield event("done", completed_payload(cached, data.message))

            return StreamingResponse(replay_response(), media_type="text/event-stream", headers={"Cache-Control": "no-cache"})

        previous_failure = history.find_ai_request_failure(actual_db_path, session_id, str(data.request_id))
        if previous_failure and (
            previous_failure["message_text"] != data.message
            or previous_failure["regenerate_from_message_id"] != data.regenerate_from_message_id
        ):
            raise HTTPException(status_code=409, detail="请求编号已用于另一条消息")

        try:
            messages = history.list_ai_messages(actual_db_path, session_id)
            if data.regenerate_from_message_id is not None:
                target_index = next(
                    (index for index, item in enumerate(messages) if item["id"] == data.regenerate_from_message_id), None
                )
                if target_index is None or messages[target_index]["role"] != "user":
                    raise ValueError("重新生成目标必须是当前会话中的用户消息")
                target = messages[target_index]
                if target["content"] != data.message:
                    raise ValueError("重新生成的内容必须与原用户消息一致")
                if any(item["role"] == "user" for item in messages[target_index + 1 :]):
                    raise ValueError("只能重新生成当前会话最后一条用户消息的回答")
                previous_messages = messages[:target_index]
            else:
                previous_messages = messages
            chat_messages = build_chat_messages(session["context"], previous_messages, data.message)
        except (KeyError, TypeError, ValueError) as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

        async def stream_response():
            lock_key = (session_id, str(data.request_id))
            lock_state = await acquire_ai_request_lock(lock_key)
            started_at = time.monotonic()
            content_chars = 0
            reasoning_chars = 0
            usage: dict[str, Any] | None = None
            provider_model_id: str | None = None
            finish_reason: str | None = None

            def diagnostic(phase: str, *, code: str | None = None) -> None:
                # Deliberately log metadata only; never include prompts, model text,
                # reasoning, credentials, or exception messages.
                payload = {
                    "request_id": str(data.request_id),
                    "model_id": provider_model_id or session["model_id"],
                    "phase": phase,
                    "has_content": content_chars > 0,
                    "has_reasoning_content": reasoning_chars > 0,
                    "content_chars": content_chars,
                    "reasoning_chars": reasoning_chars,
                    "finish_reason": finish_reason,
                    "usage": {
                        key: usage.get(key)
                        for key in ("prompt_tokens", "completion_tokens")
                        if isinstance(usage, dict) and isinstance(usage.get(key), int)
                    } if usage else None,
                    "duration_ms": round((time.monotonic() - started_at) * 1000),
                    "code": code,
                }
                ai_logger.info("ai_stream %s", json.dumps(payload, ensure_ascii=False, separators=(",", ":")))

            def persist_failure_record(code: str, stage: str, message: str) -> bool:
                try:
                    return history.save_ai_request_failure(
                        actual_db_path,
                        session_id=session_id,
                        request_id=str(data.request_id),
                        message_text=data.message,
                        regenerate_from_message_id=data.regenerate_from_message_id,
                        code=code,
                        stage=stage,
                        public_message=message,
                        created_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
                    )
                except Exception:
                    diagnostic("failure_status_persistence", code="failure_status_persist_failed")
                    return False

            def failure(code: str, stage: str, message: str) -> str:
                diagnostic(stage, code=code)
                status_persisted = persist_failure_record(code, stage, message)
                return event("error", {
                    "code": code,
                    "stage": stage,
                    "message": message,
                    "status_persisted": status_persisted,
                })

            try:
                cached = history.find_ai_request(actual_db_path, session_id, str(data.request_id))
                if cached:
                    if cached["message_text"] != data.message or cached["regenerate_from_message_id"] != data.regenerate_from_message_id:
                        yield failure("request_id_conflict", "request", "请求编号已用于另一条消息。")
                    else:
                        diagnostic("replay_saved")
                        yield event("done", completed_payload(cached, data.message))
                    return

                if not ai_public_settings()["ai_enabled"]:
                    yield failure("ai_disabled", "configuration", "AI 功能当前已关闭。")
                    return
                api_key = load_api_key()
                if not api_key:
                    yield failure("api_key_missing", "configuration", "请先配置 DeepSeek API Key。")
                    return

                parts: list[str] = []
                async for part in app.state.ai_provider.stream_chat(api_key, session["model_id"], chat_messages):
                    if isinstance(part, str):  # Compatibility for older local Mock providers.
                        chunk = AIStreamChunk(text=part)
                    elif isinstance(part, AIStreamChunk):
                        chunk = part
                    else:
                        raise AIProviderError("AI Provider 返回了无法识别的流数据。", code="provider_payload_invalid")
                    if chunk.reasoning_text:
                        reasoning_chars += len(chunk.reasoning_text)
                        yield event("reasoning", {"text": chunk.reasoning_text})
                    if chunk.text:
                        parts.append(chunk.text)
                        content_chars += len(chunk.text)
                        yield event("delta", {"text": chunk.text})
                    if chunk.usage is not None:
                        usage = chunk.usage
                    if chunk.model_id:
                        provider_model_id = chunk.model_id
                    if chunk.finish_reason:
                        finish_reason = chunk.finish_reason
                if finish_reason is None:
                    raise AIProviderError("AI 服务没有报告生成结束状态，结果未保存。", code="missing_finish_reason")
                if finish_reason != "stop":
                    reasons = {
                        "length": "AI 输出超过长度限制，没有保存回答。请缩短问题或重新生成。",
                        "content_filter": "AI 服务的内容过滤器终止了回答，没有保存结果。",
                        "tool_calls": "AI 返回了当前应用不支持的工具调用，没有保存结果。",
                        "insufficient_system_resource": "AI 服务资源不足，生成已中断，请稍后重试。",
                        "aborted": "AI 服务中断了生成，没有保存结果。",
                    }
                    code = "output_truncated" if finish_reason == "length" else "generation_incomplete"
                    raise AIProviderError(
                        reasons.get(finish_reason, "AI 未能正常完成生成，没有保存结果。"), code=code
                    )

                diagnostic("provider_complete")
                raw_output = "".join(parts)
                if not raw_output.strip():
                    raise AIProviderError("模型没有返回最终解读内容；思考内容不作为回答保存。", code="empty_final_content")
                answer = validate_ai_output(raw_output, session["context"])
                resolved_model = provider_model_id or session["model_id"]
                usage_display = estimate_cost(resolved_model, usage)
                if usage_display:
                    answer["provider"] = {
                        "model_id": resolved_model,
                        "usage": usage_display["usage"],
                        "cost_estimate": usage_display.get("estimate"),
                        "pricing_checked_at": usage_display.get("pricing_checked_at"),
                        "pricing_source_url": usage_display.get("pricing_source_url"),
                        "note": usage_display.get("note"),
                    }
                else:
                    answer["provider"] = {"model_id": resolved_model, "usage": None, "cost_estimate": None}
                created_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
                diagnostic("validated")
                try:
                    saved = history.save_ai_exchange(
                        actual_db_path, session_id=session_id, request_id=str(data.request_id),
                        message_text=data.message, assistant_content=answer, created_at=created_at,
                        regenerate_from_message_id=data.regenerate_from_message_id,
                    )
                except ValueError:
                    raise AIProviderError("AI 解读已生成，但保存会话时发生冲突；结果未确认保存。", code="persistence_conflict") from None
                except Exception:
                    raise AIProviderError("AI 解读已生成，但写入历史记录失败；请稍后使用同一请求重试。", code="persistence_failed") from None
                diagnostic("persisted")
                yield event("done", completed_payload(saved, data.message))
            except asyncio.CancelledError:
                diagnostic("cancelled", code="generation_cancelled")
                persist_failure_record("generation_cancelled", "cancelled", "生成已停止，最终解读尚未保存。")
                raise
            except AIProviderError as exc:
                stage = "persistence" if exc.code.startswith("persistence_") else "generation"
                yield failure(exc.code, stage, str(exc))
            except AIOutputValidationError as exc:
                yield failure(exc.code, "validation", str(exc))
            except ValueError:
                yield failure("processing_failed", "validation", "AI 返回内容无法处理，结果未保存。")
            except Exception:
                yield failure("internal_error", "processing", "AI 服务处理失败；未确认保存结果，请检查连接后重试。")
            finally:
                await release_ai_request_lock(lock_key, lock_state)

        return StreamingResponse(
            stream_response(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    @app.delete("/api/history/{record_id}", status_code=204, responses={404: {"model": ErrorResponse}})
    async def delete_history(record_id: int, request: Request) -> Response:
        if not history.delete(request.app.state.db_path, record_id):
            raise HTTPException(status_code=404, detail="未找到这条历史记录")
        return Response(status_code=204)

    return app


app = create_app()
