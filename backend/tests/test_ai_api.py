from __future__ import annotations

import json
import base64
import asyncio
import logging
from uuid import uuid4

from fastapi.testclient import TestClient

from backend.catalog import load_catalog
from backend.main import create_app
from backend.services.ai_provider import AIStreamChunk
from backend.services.ai_runtime import _model_visible_context
from backend.services import history


class FakeSecrets:
    def protect(self, key: str) -> str:
        return base64.b64encode(("test-protected:" + key).encode()).decode()

    def unprotect(self, value: str | None) -> str | None:
        if not value:
            return None
        decoded = base64.b64decode(value).decode()
        assert decoded.startswith("test-protected:")
        return decoded.removeprefix("test-protected:")


class FakeProvider:
    def __init__(self, answer: dict | None = None, raw_output: str | None = None):
        self.answer = answer or {
            "response_schema": "ai-response@2",
            "overview": "乾卦纯阳，初爻发动后为天风姤。",
            "traditional_basis": [{"evidence_id": "p1", "explanation": "依所选规则解释本卦动爻。"}],
            "modern_interpretation": "把问题拆成眼前可核实的条件逐项比较。",
            "suggestions": ["先收集现实信息，再作选择。"],
            "caution": "卦象不代表确定的未来。",
        }
        self.messages: list[dict[str, str]] = []
        self.call_count = 0
        self.failure: BaseException | None = None
        self.raw_output = raw_output

    async def list_models(self, api_key: str) -> list[dict[str, str]]:
        assert api_key == "sk-test"
        return [{"id": "deepseek-test-model", "owned_by": "test"}]

    async def stream_chat(self, api_key: str, model_id: str, messages: list[dict[str, str]]):
        assert api_key == "sk-test"
        assert model_id == "deepseek-test-model"
        self.call_count += 1
        self.messages = messages
        if self.failure:
            raise self.failure
        encoded = self.raw_output if self.raw_output is not None else json.dumps(self.answer, ensure_ascii=False)
        for start in range(0, len(encoded), 19):
            yield AIStreamChunk(text=encoded[start : start + 19], model_id=model_id)
        yield AIStreamChunk(
            usage={"prompt_tokens": 100, "completion_tokens": 50, "prompt_cache_hit_tokens": 40, "prompt_cache_miss_tokens": 60},
            model_id=model_id,
            finish_reason="stop",
        )


def prepare_ai(client: TestClient):
    configured = client.put("/api/ai/settings", json={"api_key": "sk-test"})
    assert configured.status_code == 200
    assert configured.json()["api_key_configured"] is True
    assert "api_key" not in configured.json()
    assert "sk-test" not in configured.text
    assert client.get("/api/ai/models").json()["models"][0]["id"] == "deepseek-test-model"
    assert client.post("/api/ai/test-connection").json()["ok"] is True
    selected = client.put("/api/ai/settings", json={"model_id": "deepseek-test-model", "ai_enabled": True})
    assert selected.status_code == 200
    assert selected.json()["ai_enabled"] is True


def send_ai(client: TestClient, session_id: int, message: str, *, request_id: str | None = None, regenerate_from_message_id: int | None = None):
    return client.post(
        f"/api/ai/sessions/{session_id}/messages",
        json={"message": message, "request_id": request_id or str(uuid4()),
              "regenerate_from_message_id": regenerate_from_message_id},
    )


def test_ai_settings_keep_secret_private_and_validate_live_model(tmp_path):
    provider = FakeProvider()
    db_path = tmp_path / "ai-settings.sqlite3"
    app = create_app(db_path=db_path, catalog=load_catalog(), ai_provider=provider, secret_store=FakeSecrets())
    with TestClient(app) as client:
        assert client.get("/api/ai/settings").json() == {
            "provider": "deepseek", "api_key_configured": False, "ai_enabled": False, "model_id": None
        }
        assert client.put("/api/ai/settings", json={"api_key": "sk-test", "model_id": "imaginary-model"}).status_code == 422
        assert history.get_setting(db_path, "deepseek_api_key_protected") is None
        prepare_ai(client)
        with history.connect(db_path) as db:
            encrypted = db.execute("SELECT value_json FROM app_settings WHERE key='deepseek_api_key_protected'").fetchone()[0]
        assert "sk-test" not in encrypted
        assert client.delete("/api/ai/settings/key").status_code == 204
        assert client.get("/api/ai/settings").json()["ai_enabled"] is False
        assert client.get("/api/ai/models").status_code == 409


def test_classical_ai_session_streams_structured_output_and_persists_context(tmp_path):
    provider = FakeProvider()
    app = create_app(
        db_path=tmp_path / "ai-chat.sqlite3", catalog=load_catalog(), ai_provider=provider, secret_store=FakeSecrets()
    )
    with TestClient(app) as client:
        prepare_ai(client)
        divination = client.post(
            "/api/divination/manual", json={"question": "要不要换岗", "lines": [9, 7, 7, 7, 7, 7]}
        ).json()
        session = client.post("/api/ai/sessions", json={"divination_id": divination["id"], "mode": "classical"})
        assert session.status_code == 200
        events = send_ai(client, session.json()["id"], "请解释初爻与我的问题")
        assert events.status_code == 200
        assert "event: delta" in events.text
        done = [line[6:] for line in events.text.splitlines() if line.startswith("data: ")]
        payloads = [json.loads(value) for value in done]
        final = next(item["message"]["content"] for item in payloads if "message" in item)
        assert final["response_schema"] == "ai-response@2"
        assert final["ruleset"] == {
            "id": divination["traditional_reading"]["ruleset_id"],
            "version": divination["traditional_reading"]["ruleset_version"],
            "name": divination["traditional_reading"]["ruleset_name"],
        }
        assert final["cited_passages"][0]["text"] == divination["traditional_reading"]["passages"][0]["text"]
        assert final["traditional_basis"][0] == {
            "evidence_id": "p1", "explanation": "依所选规则解释本卦动爻。"
        }
        assert all(message["content"] != "sk-test" for message in provider.messages)
        context_payload = json.loads(provider.messages[1]["content"].split("\n", 1)[1])
        assert context_payload["lines_bottom_to_top"][0] == {"position": 1, "value": 9, "moving": True}
        assert "najia_chart" not in context_payload
        assert context_payload["rule_versions"]["traditional_reading"]["id"] == "qiming-tongshi"
        saved = client.get(f"/api/ai/sessions/{session.json()['id']}").json()
        assert [message["role"] for message in saved["messages"]] == ["user", "assistant"]
        assert saved["failed_requests"] == []
        assert saved["messages"][1]["content"]["overview"] == final["overview"]
        assert saved["messages"][1]["request_id"]
        assert saved["messages"][1]["user_message_id"] == saved["messages"][0]["id"]
        answer_meta = saved["messages"][1]["content"]["provider"]
        assert answer_meta["usage"]["prompt_tokens"] == 100
        assert answer_meta["cost_estimate"] is None
        detail = client.get(f"/api/history/{divination['id']}").json()
        assert detail["ai_sessions"][0]["id"] == session.json()["id"]
        assert detail["ai_sessions"][0]["rule_versions"]["traditional_reading"]["id"] == "qiming-tongshi"


def test_v2_response_survives_session_api_reload_after_backend_restart(tmp_path):
    db_path = tmp_path / "ai-v2-restart.sqlite3"
    provider = FakeProvider()
    app = create_app(db_path=db_path, catalog=load_catalog(), ai_provider=provider, secret_store=FakeSecrets())
    with TestClient(app) as client:
        prepare_ai(client)
        record = client.post("/api/divination/manual", json={"question": "restart fixture", "lines": [9] * 6}).json()
        session = client.post("/api/ai/sessions", json={"divination_id": record["id"]}).json()
        response = send_ai(client, session["id"], "synthetic request")
        assert "event: done" in response.text
        before_restart = client.get(f"/api/ai/sessions/{session['id']}").json()["messages"]
        assert before_restart[1]["content"]["response_schema"] == "ai-response@2"

    restarted_provider = FakeProvider()
    restarted_app = create_app(
        db_path=db_path, catalog=load_catalog(), ai_provider=restarted_provider, secret_store=FakeSecrets()
    )
    with TestClient(restarted_app) as restarted_client:
        after_restart = restarted_client.get(f"/api/ai/sessions/{session['id']}").json()["messages"]

    assert after_restart == before_restart
    assert after_restart[1]["content"]["traditional_basis"][0]["evidence_id"] == "p1"
    assert after_restart[1]["content"]["cited_passages"][0]["text"]
    assert restarted_provider.call_count == 0


def test_najia_ai_requires_and_snapshots_verified_chart_separately(tmp_path):
    provider = FakeProvider()
    app = create_app(
        db_path=tmp_path / "ai-najia.sqlite3", catalog=load_catalog(), ai_provider=provider, secret_store=FakeSecrets()
    )
    with TestClient(app) as client:
        prepare_ai(client)
        divination = client.post("/api/divination/manual", json={"question": "排盘问题", "lines": [7] * 6}).json()
        no_chart = client.post("/api/ai/sessions", json={"divination_id": divination["id"], "mode": "najia"})
        assert no_chart.status_code == 422
        chart = client.post(
            f"/api/history/{divination['id']}/najia", json={"day_ganzhi": "甲子", "month_branch": "子"}
        ).json()
        session = client.post("/api/ai/sessions", json={"divination_id": divination["id"], "mode": "najia"}).json()
        response = send_ai(client, session["id"], "只看纳甲字段")
        assert response.status_code == 200
        context = json.loads(provider.messages[1]["content"].split("\n", 1)[1])
        assert context["mode"] == "najia"
        assert "traditional_reading" not in context
        assert context["najia_chart"] == _model_visible_context(chart)
        assert context["rule_versions"]["najia"]["id"] == "zengshan-buyi-relations"
        assert "六亲、世应" in provider.messages[0]["content"]


def test_ai_rejects_fabricated_citation_and_does_not_store_assistant_result(tmp_path):
    provider = FakeProvider({
        "response_schema": "ai-response@2", "overview": "概述",
        "traditional_basis": [{"evidence_id": "p999", "explanation": "依据"}],
        "modern_interpretation": "解释", "suggestions": ["建议"], "caution": "注意"
    })
    app = create_app(
        db_path=tmp_path / "ai-bad-cite.sqlite3", catalog=load_catalog(), ai_provider=provider, secret_store=FakeSecrets()
    )
    with TestClient(app) as client:
        prepare_ai(client)
        result = client.post("/api/divination/manual", json={"question": "引用校验", "lines": [9, 7, 7, 7, 7, 7]}).json()
        session = client.post("/api/ai/sessions", json={"divination_id": result["id"]}).json()
        response = send_ai(client, session["id"], "继续")
        assert "event: error" in response.text
        assert "当前会话未提供的证据 ID" in response.text
        error_data = next(json.loads(line[6:]) for line in response.text.splitlines() if line.startswith("data: ") and '"code"' in line)
        assert error_data["code"] == "invalid_evidence_id"
        assert error_data["stage"] == "validation"
        restored = client.get(f"/api/ai/sessions/{session['id']}").json()
        assert restored["messages"] == []
        assert len(restored["failed_requests"]) == 1
        assert restored["failed_requests"][0]["code"] == "invalid_evidence_id"
        assert restored["failed_requests"][0]["stage"] == "validation"
        assert restored["failed_requests"][0]["message_text"] == "继续"


def test_ai_request_retry_is_idempotent_and_regenerate_does_not_duplicate_user(tmp_path):
    provider = FakeProvider()
    app = create_app(db_path=tmp_path / "ai-retry.sqlite3", catalog=load_catalog(), ai_provider=provider, secret_store=FakeSecrets())
    with TestClient(app) as client:
        prepare_ai(client)
        result = client.post("/api/divination/manual", json={"question": "重试", "lines": [7] * 6}).json()
        session = client.post("/api/ai/sessions", json={"divination_id": result["id"]}).json()
        request_id = str(uuid4())
        first = send_ai(client, session["id"], "先观察条件", request_id=request_id)
        retry = send_ai(client, session["id"], "先观察条件", request_id=request_id)
        assert "event: done" in first.text and "event: done" in retry.text
        first_done = next(json.loads(line[6:]) for line in first.text.splitlines()
                          if line.startswith("data: ") and '"message"' in line)
        assert first_done["user_message"]["content"] == "先观察条件"
        assert provider.call_count == 1
        assert history.save_ai_request_failure(
            tmp_path / "ai-retry.sqlite3", session_id=session["id"], request_id=request_id,
            message_text="先观察条件", regenerate_from_message_id=None, code="stream_interrupted",
            stage="transport", public_message="前端未确认 SSE 完成。", created_at="2026-01-01T00:00:03Z",
        ) is False
        messages = client.get(f"/api/ai/sessions/{session['id']}").json()["messages"]
        assert [item["role"] for item in messages] == ["user", "assistant"]
        user_id = messages[0]["id"]
        regenerated = send_ai(
            client, session["id"], "先观察条件", request_id=str(uuid4()), regenerate_from_message_id=user_id
        )
        assert "event: done" in regenerated.text
        messages = client.get(f"/api/ai/sessions/{session['id']}").json()["messages"]
        assert [item["role"] for item in messages] == ["user", "assistant", "assistant"]
        assert messages[0]["id"] == user_id
        assert messages[1]["user_message_id"] == messages[2]["user_message_id"] == user_id
        assert messages[1]["request_id"] != messages[2]["request_id"]
        assert provider.call_count == 2


def test_ai_provider_failure_does_not_persist_user_and_same_request_can_retry(tmp_path):
    provider = FakeProvider()
    provider.failure = RuntimeError("temporary mock outage")
    app = create_app(db_path=tmp_path / "ai-failure.sqlite3", catalog=load_catalog(), ai_provider=provider, secret_store=FakeSecrets())
    with TestClient(app) as client:
        prepare_ai(client)
        result = client.post("/api/divination/manual", json={"question": "失败后重试", "lines": [7] * 6}).json()
        session = client.post("/api/ai/sessions", json={"divination_id": result["id"]}).json()
        request_id = str(uuid4())
        failed = send_ai(client, session["id"], "重试问题", request_id=request_id)
        assert "event: error" in failed.text
        error_payload = next(json.loads(line[6:]) for line in failed.text.splitlines()
                             if line.startswith("data: ") and '"code"' in line)
        assert error_payload["code"] == "internal_error"
        assert error_payload["status_persisted"] is True
        failed_session = client.get(f"/api/ai/sessions/{session['id']}").json()
        assert failed_session["messages"] == []
        assert failed_session["failed_requests"][0]["request_id"] == request_id
        assert failed_session["failed_requests"][0]["stage"] == "processing"
        assert failed_session["failed_requests"][0]["message_text"] == "重试问题"
        collision = send_ai(client, session["id"], "不同的消息", request_id=request_id)
        assert collision.status_code == 409
        provider.failure = None
        succeeded = send_ai(client, session["id"], "重试问题", request_id=request_id)
        assert "event: done" in succeeded.text
        restored_after_retry = client.get(f"/api/ai/sessions/{session['id']}").json()
        assert [item["role"] for item in restored_after_retry["messages"]] == ["user", "assistant"]
        assert restored_after_retry["failed_requests"] == []


def test_failed_request_status_survives_backend_restart(tmp_path):
    db_path = tmp_path / "ai-failure-restart.sqlite3"
    provider = FakeProvider()
    provider.failure = RuntimeError("temporary mock outage")
    app = create_app(db_path=db_path, catalog=load_catalog(), ai_provider=provider, secret_store=FakeSecrets())
    request_id = str(uuid4())
    with TestClient(app) as client:
        prepare_ai(client)
        result = client.post("/api/divination/manual", json={"question": "失败后恢复", "lines": [7] * 6}).json()
        session = client.post("/api/ai/sessions", json={"divination_id": result["id"]}).json()
        failed = send_ai(client, session["id"], "仅用于恢复测试", request_id=request_id)
        assert "event: error" in failed.text

    restarted_app = create_app(
        db_path=db_path, catalog=load_catalog(), ai_provider=FakeProvider(), secret_store=FakeSecrets()
    )
    with TestClient(restarted_app) as restarted_client:
        restored = restarted_client.get(f"/api/ai/sessions/{session['id']}").json()

    assert restored["messages"] == []
    assert len(restored["failed_requests"]) == 1
    assert restored["failed_requests"][0]["request_id"] == request_id
    assert restored["failed_requests"][0]["message_text"] == "仅用于恢复测试"
    assert restored["failed_requests"][0]["code"] == "internal_error"


def test_najia_mode_rejects_classical_passage_citations(tmp_path):
    provider = FakeProvider({
        "response_schema": "ai-response@2", "overview": "只按排盘字段说明。",
        "traditional_basis": [{"evidence_id": "p1", "explanation": "没有引用纳甲规则。"}],
        "modern_interpretation": "仅供整理思路。",
        "suggestions": ["核对现实条件。"], "caution": "不表示确定未来。",
    })
    app = create_app(db_path=tmp_path / "ai-mode-isolation.sqlite3", catalog=load_catalog(), ai_provider=provider, secret_store=FakeSecrets())
    with TestClient(app) as client:
        prepare_ai(client)
        record = client.post("/api/divination/manual", json={"question": "模式隔离", "lines": [7] * 6}).json()
        client.post(f"/api/history/{record['id']}/najia", json={"day_ganzhi": "甲子", "month_branch": "子"})
        session = client.post("/api/ai/sessions", json={"divination_id": record["id"], "mode": "najia"}).json()
        response = send_ai(client, session["id"], "只看纳甲")
        assert "当前会话未提供的证据 ID" in response.text
        restored = client.get(f"/api/ai/sessions/{session['id']}").json()
        assert restored["messages"] == []
        assert len(restored["failed_requests"]) == 1
        assert restored["failed_requests"][0]["code"] == "invalid_evidence_id"
        assert restored["failed_requests"][0]["stage"] == "validation"


def test_classical_mode_rejects_evidence_id_from_another_mode(tmp_path):
    provider = FakeProvider({
        "response_schema": "ai-response@2", "overview": "仅按本卦原文概述。",
        "traditional_basis": [{"evidence_id": "qiming-tongshi", "explanation": "本卦原文资料。"}],
        "modern_interpretation": "仅供整理思路。",
        "suggestions": ["结合现实信息判断。"], "caution": "不代表确定未来。",
    })
    app = create_app(db_path=tmp_path / "classical-citation-isolation.sqlite3", catalog=load_catalog(),
                     ai_provider=provider, secret_store=FakeSecrets())
    with TestClient(app) as client:
        prepare_ai(client)
        record = client.post(
            "/api/divination/manual", json={"question": "经文模式引用隔离", "lines": [9, 7, 7, 7, 7, 7]}
        ).json()
        session = client.post("/api/ai/sessions", json={"divination_id": record["id"], "mode": "classical"}).json()
        response = send_ai(client, session["id"], "仅按本卦原文说明")
        assert "当前会话未提供的证据 ID" in response.text
        assert '"cited_rule_ids"' not in provider.messages[0]["content"]
        restored = client.get(f"/api/ai/sessions/{session['id']}").json()
        assert restored["messages"] == []
        assert len(restored["failed_requests"]) == 1
        assert restored["failed_requests"][0]["code"] == "invalid_evidence_id"
        assert restored["failed_requests"][0]["stage"] == "validation"


def test_deepseek_length_finish_reason_is_typed_and_never_saved(tmp_path):
    class TruncatedProvider(FakeProvider):
        async def stream_chat(self, api_key: str, model_id: str, messages: list[dict[str, str]]):
            self.call_count += 1
            self.messages = messages
            yield AIStreamChunk(text='{"overview":"partial', model_id=model_id)
            yield AIStreamChunk(
                usage={"prompt_tokens": 1400, "completion_tokens": 2400},
                model_id=model_id,
                finish_reason="length",
            )

    provider = TruncatedProvider()
    db_path = tmp_path / "ai-truncated.sqlite3"
    app = create_app(db_path=db_path, catalog=load_catalog(), ai_provider=provider, secret_store=FakeSecrets())
    with TestClient(app) as client:
        prepare_ai(client)
        record = client.post("/api/divination/manual", json={"question": "合成截断测试", "lines": [7] * 6}).json()
        session = client.post("/api/ai/sessions", json={"divination_id": record["id"]}).json()
        response = send_ai(client, session["id"], "合成请求")
        error_event = next(line[6:] for line in response.text.splitlines() if line.startswith("data: ") and '"code"' in line)
        error_payload = json.loads(error_event)
        assert error_payload["code"] == "output_truncated"
        assert error_payload["stage"] == "generation"
        assert client.get(f"/api/ai/sessions/{session['id']}").json()["messages"] == []
        assert history.find_ai_request(db_path, session["id"], str(json.loads(response.request.content)["request_id"])) is None


def test_invalid_json_has_a_distinct_error_code(tmp_path):
    provider = FakeProvider(raw_output="not a JSON answer")
    db_path = tmp_path / "ai-invalid-json.sqlite3"
    app = create_app(db_path=db_path, catalog=load_catalog(), ai_provider=provider, secret_store=FakeSecrets())
    with TestClient(app) as client:
        prepare_ai(client)
        record = client.post("/api/divination/manual", json={"question": "合成 JSON 测试", "lines": [9, 7, 7, 7, 7, 7]}).json()
        session = client.post("/api/ai/sessions", json={"divination_id": record["id"]}).json()
        response = send_ai(client, session["id"], "合成请求")
        error_payload = next(json.loads(line[6:]) for line in response.text.splitlines() if line.startswith("data: ") and '"code"' in line)
        assert error_payload["code"] == "invalid_json"
        assert error_payload["stage"] == "validation"
        assert client.get(f"/api/ai/sessions/{session['id']}").json()["messages"] == []


def test_quoted_modern_explanation_is_not_treated_as_a_canonical_citation(tmp_path):
    provider = FakeProvider({
        "response_schema": "ai-response@2", "overview": "概述",
        "traditional_basis": [{"evidence_id": "p1", "explanation": "说明爻辞对处境的提示。"}],
        "modern_interpretation": "这句“先核对实际条件”是现代归纳，不是典籍原文。",
        "suggestions": ["核实信息。"], "caution": "不能作为确定预测。",
    })
    db_path = tmp_path / "ai-altered-quotation.sqlite3"
    app = create_app(db_path=db_path, catalog=load_catalog(), ai_provider=provider, secret_store=FakeSecrets())
    with TestClient(app) as client:
        prepare_ai(client)
        record = client.post("/api/divination/manual", json={"question": "合成引文校验", "lines": [7] * 6}).json()
        session = client.post("/api/ai/sessions", json={"divination_id": record["id"]}).json()
        response = send_ai(client, session["id"], "合成请求")
        assert "event: done" in response.text
        final = next(json.loads(line[6:])["message"]["content"] for line in response.text.splitlines()
                     if line.startswith("data: ") and '"message"' in line)
        local_passages = client.get(f"/api/history/{record['id']}").json()["traditional_reading"]["passages"]
        assert final["cited_passages"][0]["text"] == local_passages[0]["text"]
        assert "先核对实际条件" in final["modern_interpretation"]
        assert "unverified_quotation" not in response.text


def test_reasoning_and_final_json_are_separate_and_only_final_answer_is_saved(tmp_path):
    class ReasoningProvider(FakeProvider):
        async def stream_chat(self, api_key: str, model_id: str, messages: list[dict[str, str]]):
            self.call_count += 1
            self.messages = messages
            yield AIStreamChunk(reasoning_text="MOCK_REASONING_SENTINEL", model_id=model_id)
            encoded = json.dumps(self.answer, ensure_ascii=False)
            for char in encoded:
                yield AIStreamChunk(text=char, model_id=model_id)
            yield AIStreamChunk(
                usage={"prompt_tokens": 100, "completion_tokens": 50},
                model_id=model_id,
                finish_reason="stop",
            )

    provider = ReasoningProvider()
    db_path = tmp_path / "ai-reasoning-separation.sqlite3"
    app = create_app(db_path=db_path, catalog=load_catalog(), ai_provider=provider, secret_store=FakeSecrets())
    with TestClient(app) as client:
        prepare_ai(client)
        record = client.post("/api/divination/manual", json={"question": "MOCK_QUESTION_SENTINEL", "lines": [7] * 6}).json()
        session = client.post("/api/ai/sessions", json={"divination_id": record["id"]}).json()
        response = send_ai(client, session["id"], "MOCK_USER_SENTINEL")
        assert "event: reasoning" in response.text
        assert "event: delta" in response.text
        final = next(json.loads(line[6:])["message"] for line in response.text.splitlines()
                     if line.startswith("data: ") and '"message"' in line)
        assert final["content"]["overview"] == provider.answer["overview"]
        saved = client.get(f"/api/ai/sessions/{session['id']}").json()["messages"]
        assert [item["role"] for item in saved] == ["user", "assistant"]
        assert "MOCK_REASONING_SENTINEL" not in json.dumps(saved, ensure_ascii=False)


def test_reasoning_without_final_content_is_not_treated_as_a_completed_answer(tmp_path):
    class ReasoningOnlyProvider(FakeProvider):
        async def stream_chat(self, api_key: str, model_id: str, messages: list[dict[str, str]]):
            self.call_count += 1
            yield AIStreamChunk(reasoning_text="mock-only thought", model_id=model_id)
            yield AIStreamChunk(finish_reason="stop", model_id=model_id)

    provider = ReasoningOnlyProvider()
    app = create_app(db_path=tmp_path / "ai-empty-final.sqlite3", catalog=load_catalog(), ai_provider=provider,
                     secret_store=FakeSecrets())
    with TestClient(app) as client:
        prepare_ai(client)
        record = client.post("/api/divination/manual", json={"question": "合成空回答测试", "lines": [7] * 6}).json()
        session = client.post("/api/ai/sessions", json={"divination_id": record["id"]}).json()
        response = send_ai(client, session["id"], "合成请求")
        error = next(json.loads(line[6:]) for line in response.text.splitlines()
                     if line.startswith("data: ") and '"code"' in line)
        assert error["code"] == "empty_final_content"
        assert error["stage"] == "generation"
        assert client.get(f"/api/ai/sessions/{session['id']}").json()["messages"] == []


def test_single_json_code_fence_is_removed_without_relaxing_schema_or_citation_checks(tmp_path):
    provider = FakeProvider()
    provider.raw_output = "```json\n" + json.dumps(provider.answer, ensure_ascii=False) + "\n```"
    app = create_app(db_path=tmp_path / "ai-json-fence.sqlite3", catalog=load_catalog(), ai_provider=provider,
                     secret_store=FakeSecrets())
    with TestClient(app) as client:
        prepare_ai(client)
        record = client.post("/api/divination/manual", json={"question": "合成围栏测试", "lines": [7] * 6}).json()
        session = client.post("/api/ai/sessions", json={"divination_id": record["id"]}).json()
        response = send_ai(client, session["id"], "合成请求")
        assert "event: done" in response.text
        assert len(client.get(f"/api/ai/sessions/{session['id']}").json()["messages"]) == 2


def test_ai_diagnostics_log_only_metadata_not_prompts_reasoning_or_answer(tmp_path, caplog):
    class DiagnosticProvider(FakeProvider):
        async def stream_chat(self, api_key: str, model_id: str, messages: list[dict[str, str]]):
            self.call_count += 1
            self.messages = messages
            yield AIStreamChunk(reasoning_text="PRIVATE_REASONING_SENTINEL", model_id=model_id)
            answer = {**self.answer, "overview": "PRIVATE_ANSWER_SENTINEL"}
            for char in json.dumps(answer, ensure_ascii=False):
                yield AIStreamChunk(text=char, model_id=model_id)
            yield AIStreamChunk(finish_reason="stop", model_id=model_id)

    provider = DiagnosticProvider()
    app = create_app(db_path=tmp_path / "ai-diagnostics.sqlite3", catalog=load_catalog(), ai_provider=provider,
                     secret_store=FakeSecrets())
    with TestClient(app) as client, caplog.at_level(logging.INFO, logger="backend.ai"):
        prepare_ai(client)
        record = client.post("/api/divination/manual", json={"question": "PRIVATE_QUESTION_SENTINEL", "lines": [7] * 6}).json()
        session = client.post("/api/ai/sessions", json={"divination_id": record["id"]}).json()
        request_id = str(uuid4())
        send_ai(client, session["id"], "PRIVATE_MESSAGE_SENTINEL", request_id=request_id)
    assert request_id in caplog.text
    assert "deepseek-test-model" in caplog.text
    for secret_text in ("PRIVATE_QUESTION_SENTINEL", "PRIVATE_MESSAGE_SENTINEL", "PRIVATE_ANSWER_SENTINEL",
                        "PRIVATE_REASONING_SENTINEL", "sk-test"):
        assert secret_text not in caplog.text


def test_cancelled_ai_generation_saves_no_partial_messages(tmp_path):
    provider = FakeProvider()
    provider.failure = asyncio.CancelledError()
    app = create_app(db_path=tmp_path / "ai-cancel.sqlite3", catalog=load_catalog(), ai_provider=provider, secret_store=FakeSecrets())
    with TestClient(app) as client:
        prepare_ai(client)
        record = client.post("/api/divination/manual", json={"question": "停止生成", "lines": [7] * 6}).json()
        session = client.post("/api/ai/sessions", json={"divination_id": record["id"]}).json()
        try:
            send_ai(client, session["id"], "可中断的问题")
        except asyncio.CancelledError:
            pass
        restored = client.get(f"/api/ai/sessions/{session['id']}").json()
        assert restored["messages"] == []
        assert len(restored["failed_requests"]) == 1
        assert restored["failed_requests"][0]["code"] == "generation_cancelled"
        assert restored["failed_requests"][0]["stage"] == "cancelled"
        assert "尚未保存" in restored["failed_requests"][0]["message"]


def test_legacy_records_remain_readable_and_can_start_ai_session(tmp_path):
    db_path = tmp_path / "ai-legacy.sqlite3"
    history.initialize(db_path)
    client_catalog = load_catalog()
    from backend.main import _build_result

    old_result = _build_result(
        question="旧数据", method="manual", lines=(7, 7, 7, 7, 7, 7), coin_faces=None, catalog=client_catalog
    )
    old_result.pop("traditional_reading")
    record_id = history.create(db_path, old_result, "2026-01-01T00:00:00+00:00")
    provider = FakeProvider()
    app = create_app(db_path=db_path, catalog=client_catalog, ai_provider=provider, secret_store=FakeSecrets())
    with TestClient(app) as client:
        prepare_ai(client)
        assert client.get(f"/api/history/{record_id}").status_code == 200
        session = client.post("/api/ai/sessions", json={"divination_id": record_id})
        assert session.status_code == 200


def test_legacy_v313_assistant_message_is_returned_without_migration(tmp_path):
    db_path = tmp_path / "ai-v313-session.sqlite3"
    provider = FakeProvider()
    app = create_app(db_path=db_path, catalog=load_catalog(), ai_provider=provider, secret_store=FakeSecrets())
    legacy_content = {
        "overview": "旧版概述",
        "cited_passages": [{
            "id": "p1", "label": "卦辞", "text": "已保存的本地原文",
            "source_url": "https://local.invalid/source", "source_revision_id": 12,
        }],
        "cited_rules": [],
        "traditional_basis": "旧版字符串依据",
        "modern_interpretation": "旧版现代解释",
        "suggestions": ["旧版建议"],
        "ruleset": {"id": "qiming-tongshi", "version": "1.0.0", "name": "启蒙通释"},
        "mode": "classical",
        "caution": "旧版提示",
    }
    with TestClient(app) as client:
        prepare_ai(client)
        record = client.post("/api/divination/manual", json={"question": "compatibility fixture", "lines": [7] * 6}).json()
        session = client.post("/api/ai/sessions", json={"divination_id": record["id"]}).json()
        history.add_ai_message(db_path, session["id"], "user", "saved user turn", "2026-01-01T00:00:00Z")
        history.add_ai_message(db_path, session["id"], "assistant", legacy_content, "2026-01-01T00:00:01Z")

        restored = client.get(f"/api/ai/sessions/{session['id']}").json()

    assert restored["messages"][1]["content"] == legacy_content
    assert restored["messages"][1]["content"]["traditional_basis"] == "旧版字符串依据"
    assert provider.call_count == 0
