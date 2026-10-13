from __future__ import annotations

import asyncio
import json

import httpx
import pytest

from backend.services.ai_provider import AIProviderError, DeepSeekProvider


def install_http_transport(monkeypatch, handler):
    original = httpx.AsyncClient
    transport = httpx.MockTransport(handler)

    def factory(*args, **kwargs):
        kwargs["transport"] = transport
        return original(*args, **kwargs)

    monkeypatch.setattr("backend.services.ai_provider.httpx.AsyncClient", factory)


def test_deepseek_provider_reads_actual_model_ids_and_parses_sse(monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["authorization"] == "Bearer sk-local-test"
        if request.url.path == "/models":
            return httpx.Response(200, json={"object": "list", "data": [{"id": "deepseek-live-id", "owned_by": "deepseek"}]})
        body = json.loads(request.content)
        assert body["model"] == "deepseek-live-id"
        assert body["stream"] is True
        assert body["stream_options"] == {"include_usage": True}
        assert body["response_format"] == {"type": "json_object"}
        events = (
            'data: {"choices":[{"delta":{"content":"{\\"ok\\":"}}]}\n\n'
            'data: {"choices":[{"delta":{"content":"true}"},"finish_reason":"stop"}],"model":"deepseek-live-id",'
            '"usage":{"prompt_tokens":12,"completion_tokens":3,"prompt_cache_hit_tokens":4,"prompt_cache_miss_tokens":8}}\n\n'
            'data: [DONE]\n\n'
        )
        return httpx.Response(200, headers={"content-type": "text/event-stream"}, content=events.encode())

    install_http_transport(monkeypatch, handler)
    provider = DeepSeekProvider()

    async def run():
        models = await provider.list_models("sk-local-test")
        chunks = [part async for part in provider.stream_chat("sk-local-test", "deepseek-live-id", [{"role": "user", "content": "hello"}])]
        return models, chunks

    models, chunks = asyncio.run(run())
    assert models == [{"id": "deepseek-live-id", "owned_by": "deepseek"}]
    assert "".join(item.text for item in chunks) == '{"ok":true}'
    assert chunks[-1].finish_reason == "stop"
    assert chunks[-1].model_id == "deepseek-live-id"
    assert chunks[-1].usage["prompt_tokens"] == 12


def test_deepseek_provider_keeps_reasoning_and_final_content_separate(monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        assert body["max_tokens"] == 8192
        events = (
            'data: {"choices":[{"delta":{"reasoning_content":"mock-only reasoning"},"finish_reason":null}]}\n\n'
            'data: {"choices":[{"delta":{"content":"{\\"overview\\":\\"final\\"}"},"finish_reason":null}]}\n\n'
            'data: {"choices":[{"delta":{"content":""},"finish_reason":"stop"}],"model":"deepseek-v4-pro",'
            '"usage":{"prompt_tokens":9,"completion_tokens":4}}\n\n'
            'data: [DONE]\n\n'
        )
        return httpx.Response(200, headers={"content-type": "text/event-stream"}, content=events.encode())

    install_http_transport(monkeypatch, handler)

    async def run():
        return [
            part async for part in DeepSeekProvider().stream_chat(
                "sk-local-test", "deepseek-v4-pro", [{"role": "user", "content": "synthetic"}]
            )
        ]

    chunks = asyncio.run(run())
    assert chunks[0].reasoning_text == "mock-only reasoning"
    assert chunks[0].text == ""
    assert "".join(item.text for item in chunks) == '{"overview":"final"}'
    assert chunks[-1].finish_reason == "stop"


def test_deepseek_provider_maps_auth_error_without_exposing_response_body(monkeypatch):
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"detail": "private provider diagnostics"})

    install_http_transport(monkeypatch, handler)
    provider = DeepSeekProvider()
    with pytest.raises(AIProviderError, match="API Key") as error:
        asyncio.run(provider.list_models("sk-local-test"))
    assert "private provider diagnostics" not in str(error.value)
    assert error.value.status_code == 401


@pytest.mark.parametrize(
    ("status", "message"),
    [(402, "余额不足"), (429, "过于频繁"), (503, "服务繁忙")],
)
def test_deepseek_provider_maps_balance_rate_and_overload_errors(monkeypatch, status, message):
    install_http_transport(monkeypatch, lambda _: httpx.Response(status, json={"detail": "do not expose provider body"}))
    with pytest.raises(AIProviderError, match=message) as error:
        asyncio.run(DeepSeekProvider().list_models("sk-local-test"))
    assert error.value.status_code == status
    assert "do not expose" not in str(error.value)


def test_deepseek_provider_rejects_a_stream_without_done_marker(monkeypatch):
    def handler(_: httpx.Request) -> httpx.Response:
        body = 'data: {"choices":[{"delta":{"content":"{}"},"finish_reason":"stop"}]}\n\n'
        return httpx.Response(200, headers={"content-type": "text/event-stream"}, content=body.encode())

    install_http_transport(monkeypatch, handler)
    async def run():
        return [item async for item in DeepSeekProvider().stream_chat("sk-local-test", "deepseek-flash", [])]

    with pytest.raises(AIProviderError, match="提前结束"):
        asyncio.run(run())
