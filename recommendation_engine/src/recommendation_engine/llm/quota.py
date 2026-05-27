"""Gemini quota / rate-limit helpers."""

from __future__ import annotations

import json
import re


class GeminiQuotaExhaustedError(RuntimeError):
    """Daily or hard quota exhausted — retrying will not help until quota resets."""


def is_daily_quota_error(exc: BaseException) -> bool:
    text = str(exc)
    return (
        "PerDay" in text
        or "PerDayPerProject" in text
        or "FreeTier" in text and "quotaValue" in text
        or "generate_content_free_tier_requests" in text
    )


def is_rate_limit_error(exc: BaseException) -> bool:
    if is_daily_quota_error(exc):
        return True
    name = type(exc).__name__
    if name == "ClientError" and "429" in str(exc):
        return True
    return "RESOURCE_EXHAUSTED" in str(exc)


def is_retryable_gemini_error(exc: BaseException) -> bool:
    if is_daily_quota_error(exc):
        return False
    text = str(exc)
    if "429" in text or "RESOURCE_EXHAUSTED" in text:
        return True
    if "503" in text or "UNAVAILABLE" in text:
        return True
    code = getattr(exc, "status_code", None)
    return code in (429, 503)


def retry_seconds_from_error(exc: BaseException) -> float | None:
    text = str(exc)
    match = re.search(r"retry in (\d+(?:\.\d+)?)s", text, re.I)
    if match:
        return float(match.group(1)) + 2.0
    match = re.search(r"retryDelay['\"]?\s*[:=]\s*['\"]?(\d+)", text, re.I)
    if match:
        return float(match.group(1)) + 2.0
    try:
        if "{" in text:
            start = text.find("{")
            payload = json.loads(text[start:])
            err = payload.get("error", payload)
            details = err.get("details", []) if isinstance(err, dict) else []
            for item in details:
                if isinstance(item, dict) and "retryDelay" in item:
                    delay = str(item["retryDelay"]).rstrip("s")
                    return float(delay) + 2.0
    except (json.JSONDecodeError, TypeError, ValueError):
        pass
    return None


def quota_error_message(exc: BaseException, *, model: str) -> str:
    hint = (
        f"Gemini quota exceeded for model={model}. "
        "Free tier gemini-2.5-flash allows ~20 generate requests/day — "
        "set EG_MODEL_*=gemini-2.0-flash (separate quota), enable EG_LLM_CONSERVE=1, "
        "or enable billing: https://ai.google.dev/gemini-api/docs/rate-limits"
    )
    return f"{hint} Original: {str(exc)[:400]}"
