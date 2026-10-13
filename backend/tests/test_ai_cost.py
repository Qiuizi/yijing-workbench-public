from __future__ import annotations

from backend.services.ai_cost import estimate_cost


def test_deepseek_flash_estimate_uses_cache_and_peak_off_peak_prices():
    result = estimate_cost(
        "deepseek-flash",
        {
            "prompt_tokens": 100,
            "completion_tokens": 50,
            "prompt_cache_hit_tokens": 40,
            "prompt_cache_miss_tokens": 60,
        },
    )
    assert result is not None
    assert result["usage"] == {
        "prompt_tokens": 100,
        "completion_tokens": 50,
        "cache_hit_tokens": 40,
        "cache_miss_tokens": 60,
    }
    assert result["estimate"] == {"currency": "USD", "off_peak": 0.00003912, "peak": 0.00007824}
    assert result["pricing_checked_at"] == "2026-09-24"


def test_unknown_model_displays_usage_without_inventing_price():
    result = estimate_cost(
        "model-from-live-list",
        {"prompt_tokens": 10, "completion_tokens": 5, "prompt_cache_hit_tokens": 2, "prompt_cache_miss_tokens": 8},
    )
    assert result is not None
    assert result["estimate"] is None


def test_incomplete_or_inconsistent_usage_has_no_estimate():
    assert estimate_cost("deepseek-flash", {"prompt_tokens": 10, "completion_tokens": 3}) is None
    assert estimate_cost(
        "deepseek-flash",
        {"prompt_tokens": 10, "completion_tokens": 3, "prompt_cache_hit_tokens": 8, "prompt_cache_miss_tokens": 1},
    ) is None
