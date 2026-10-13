"""DeepSeek HTTP provider and a typed stream contract for the API layer."""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Any, Protocol

import httpx


class AIProviderError(RuntimeError):
    def __init__(self, message: str, *, status_code: int | None = None, code: str = "provider_error"):
        super().__init__(message)
        self.status_code = status_code
        self.code = code


@dataclass(frozen=True)
class AIStreamChunk:
    """One provider stream frame; usage/model/finish_reason usually arrive last."""

    text: str = ""
    reasoning_text: str = ""
    usage: dict[str, Any] | None = None
    model_id: str | None = None
    finish_reason: str | None = None


class AIProvider(Protocol):
    async def list_models(self, api_key: str) -> list[dict[str, str]]: ...

    async def stream_chat(
        self, api_key: str, model_id: str, messages: list[dict[str, str]]
    ) -> AsyncIterator[AIStreamChunk]: ...


class DeepSeekProvider:
    base_url = "https://api.deepseek.com"

    async def list_models(self, api_key: str) -> list[dict[str, str]]:
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(20.0, connect=8.0)) as client:
                response = await client.get(f"{self.base_url}/models", headers={"Authorization": f"Bearer {api_key}"})
                response.raise_for_status()
            payload = response.json()
            if not isinstance(payload, dict) or not isinstance(payload.get("data"), list):
                raise AIProviderError("DeepSeek 返回的模型列表格式无效")
            return [
                {"id": model["id"], "owned_by": str(model.get("owned_by", ""))}
                for model in payload["data"]
                if isinstance(model, dict) and isinstance(model.get("id"), str)
            ]
        except AIProviderError:
            raise
        except httpx.HTTPStatusError as exc:
            raise self._http_error(exc.response.status_code) from exc
        except httpx.TimeoutException as exc:
            raise AIProviderError("连接 DeepSeek 超时，请检查网络后重试") from exc
        except (httpx.HTTPError, ValueError) as exc:
            raise AIProviderError("无法连接 DeepSeek 模型服务，请检查网络与服务状态") from exc

    async def stream_chat(
        self, api_key: str, model_id: str, messages: list[dict[str, str]]
    ) -> AsyncIterator[AIStreamChunk]:
        body = {
            "model": model_id,
            "messages": messages,
            "stream": True,
            "stream_options": {"include_usage": True},
            "response_format": {"type": "json_object"},
            # DeepSeek thinking output and the JSON answer share this completion budget.
            "max_tokens": 8192,
        }
        received_done = False
        finish_reason: str | None = None
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(150.0, connect=8.0)) as client:
                async with client.stream(
                    "POST",
                    f"{self.base_url}/chat/completions",
                    headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                    json=body,
                ) as response:
                    if response.is_error:
                        await response.aread()
                        raise self._http_error(response.status_code)
                    async for line in response.aiter_lines():
                        if not line.startswith("data:"):
                            continue
                        raw = line[5:].strip()
                        if raw == "[DONE]":
                            received_done = True
                            break
                        try:
                            chunk = json.loads(raw)
                            if not isinstance(chunk, dict):
                                raise TypeError
                            choices = chunk.get("choices", [])
                            if not isinstance(choices, list):
                                raise TypeError
                            choice = choices[0] if choices else {}
                            if not isinstance(choice, dict):
                                raise TypeError
                            delta = choice.get("delta") or {}
                            if not isinstance(delta, dict):
                                raise TypeError
                            content = delta.get("content")
                            if content is not None and not isinstance(content, str):
                                raise TypeError
                            reasoning_content = delta.get("reasoning_content")
                            if reasoning_content is not None and not isinstance(reasoning_content, str):
                                raise TypeError
                            reason = choice.get("finish_reason")
                            if reason is not None and not isinstance(reason, str):
                                raise TypeError
                            finish_reason = reason or finish_reason
                            usage = chunk.get("usage")
                            if usage is not None and not isinstance(usage, dict):
                                raise TypeError
                            model = chunk.get("model")
                            if model is not None and not isinstance(model, str):
                                raise TypeError
                            yield AIStreamChunk(
                                text=content or "",
                                reasoning_text=reasoning_content or "",
                                usage=usage,
                                model_id=model,
                                finish_reason=reason,
                            )
                        except (ValueError, AttributeError, IndexError, TypeError):
                            raise AIProviderError(
                                "DeepSeek 返回了无法读取的流式数据", code="provider_payload_invalid"
                            ) from None
            if not received_done:
                raise AIProviderError("DeepSeek 流式连接提前结束，请重试", code="stream_incomplete")
            if finish_reason is None:
                raise AIProviderError("DeepSeek 未返回生成结束原因，请重试", code="missing_finish_reason")
        except AIProviderError:
            raise
        except httpx.TimeoutException as exc:
            raise AIProviderError("DeepSeek 响应超时，请缩短问题或稍后重试", code="provider_timeout") from exc
        except httpx.HTTPError as exc:
            raise AIProviderError("与 DeepSeek 的流式连接中断，请重试", code="provider_disconnected") from exc

    @staticmethod
    def _http_error(status_code: int) -> AIProviderError:
        messages = {
            400: "DeepSeek 拒绝了请求，请刷新模型列表或缩短输入内容",
            401: "DeepSeek API Key 无效或已失效",
            402: "DeepSeek 账户余额不足",
            403: "DeepSeek 账户无权调用所选模型",
            408: "DeepSeek 请求超时，请稍后重试",
            429: "DeepSeek 请求过于频繁，请稍后重试",
            500: "DeepSeek 服务内部错误，请稍后重试",
            502: "DeepSeek 上游服务暂不可用，请稍后重试",
            503: "DeepSeek 服务繁忙，请稍后重试",
            504: "DeepSeek 服务响应超时，请稍后重试",
        }
        return AIProviderError(
            messages.get(status_code, f"DeepSeek 请求失败（HTTP {status_code}）"),
            status_code=status_code,
            code="provider_http_error",
        )
