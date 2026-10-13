"""Conservative DeepSeek usage display; unknown models never get guessed prices."""

from __future__ import annotations

from typing import Any


DEEPSEEK_PRICING_CHECKED_AT = "2026-09-24"
DEEPSEEK_PRICING_SOURCE = "https://api-docs.deepseek.com/quick_start/pricing/"
_USD_PER_MILLION = {
    "deepseek-flash": {
        "off_peak": {"cache_hit": 0.003, "cache_miss": 0.15, "output": 0.60},
        "peak": {"cache_hit": 0.006, "cache_miss": 0.30, "output": 1.20},
    },
}


def estimate_cost(model_id: str, usage: dict[str, Any] | None) -> dict[str, Any] | None:
    """Return token usage and an official-price range only when all inputs are known."""
    if not usage:
        return None
    price = _USD_PER_MILLION.get(model_id)
    prompt = usage.get("prompt_tokens")
    output = usage.get("completion_tokens")
    details = usage.get("prompt_tokens_details")
    details = details if isinstance(details, dict) else {}
    hit = usage.get("prompt_cache_hit_tokens", details.get("cached_tokens"))
    miss = usage.get("prompt_cache_miss_tokens")
    if miss is None and type(prompt) is int and type(hit) is int:
        miss = prompt - hit
    values = {"prompt_tokens": prompt, "completion_tokens": output, "cache_hit_tokens": hit, "cache_miss_tokens": miss}
    if any(type(value) is not int or value < 0 for value in values.values()):
        return None
    if hit + miss != prompt or output > 10_000_000:
        return None
    result: dict[str, Any] = {"usage": values}
    if price is None:
        result["estimate"] = None
        result["note"] = "该模型没有本地已核验的价格表，仅显示供应商返回的 Token 用量。"
        return result

    def amount(period: str) -> float:
        rates = price[period]
        return round((hit * rates["cache_hit"] + miss * rates["cache_miss"] + output * rates["output"]) / 1_000_000, 8)

    result["estimate"] = {"currency": "USD", "off_peak": amount("off_peak"), "peak": amount("peak")}
    result["pricing_checked_at"] = DEEPSEEK_PRICING_CHECKED_AT
    result["pricing_source_url"] = DEEPSEEK_PRICING_SOURCE
    result["note"] = "按官方公布的缓存命中/未命中与峰谷 Token 单价估算；实际扣费以 DeepSeek 账单为准。"
    return result
