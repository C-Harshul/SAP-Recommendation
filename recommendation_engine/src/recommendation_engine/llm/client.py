"""Google Gemini client for structured pipeline outputs."""

from __future__ import annotations

import json
import time
from typing import TypeVar

import structlog
from pydantic import BaseModel, ValidationError
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

from recommendation_engine.config.settings import Settings, get_settings
from recommendation_engine.llm.json_parse import parse_json_response
from recommendation_engine.llm.quota import (
    GeminiQuotaExhaustedError,
    is_daily_quota_error,
    is_retryable_gemini_error,
    quota_error_message,
    retry_seconds_from_error,
)

T = TypeVar("T", bound=BaseModel)

log = structlog.get_logger()


class LLMNotConfiguredError(RuntimeError):
    pass


class LLMClient:
    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()
        if not self._settings.use_live_llm:
            raise LLMNotConfiguredError(
                "Live LLM required. Set EG_LLM_MODE=live and GOOGLE_API_KEY (or GEMINI_API_KEY) in .env"
            )
        from google import genai

        self._client = genai.Client(api_key=self._settings.google_api_key)
        self._last_call_at: float = 0.0
        self._request_count: int = 0

    def _check_budget(self, model: str) -> None:
        budget = self._settings.llm_max_requests_per_run
        if budget is not None and self._request_count >= budget:
            raise GeminiQuotaExhaustedError(
                f"EG_LLM_MAX_REQUESTS_PER_RUN={budget} reached for this pipeline run. "
                "Raise the limit, enable EG_LLM_CONSERVE=1, or use gemini-2.0-flash."
            )

    def _throttle(self) -> None:
        delay = max(0.0, self._settings.llm_request_delay_seconds)
        if delay <= 0:
            return
        elapsed = time.monotonic() - self._last_call_at
        if elapsed < delay:
            time.sleep(delay - elapsed)

    @retry(
        retry=retry_if_exception(is_retryable_gemini_error),
        wait=wait_exponential(multiplier=2, min=10, max=120),
        stop=stop_after_attempt(6),
        reraise=True,
    )
    def _generate(self, *, model: str, user: str, config) -> str:
        self._check_budget(model)
        self._throttle()
        try:
            response = self._client.models.generate_content(
                model=model,
                contents=user,
                config=config,
            )
        except Exception as exc:
            if is_daily_quota_error(exc):
                raise GeminiQuotaExhaustedError(quota_error_message(exc, model=model)) from exc
            if is_retryable_gemini_error(exc):
                wait_s = retry_seconds_from_error(exc)
                if wait_s:
                    log.warning("gemini_rate_limit_wait", model=model, wait_seconds=wait_s)
                    time.sleep(wait_s)
            raise
        finally:
            self._last_call_at = time.monotonic()
            self._request_count += 1

        text = response.text or ""
        if not text.strip():
            raise RuntimeError(f"Gemini returned empty response for model={model}")
        finish = None
        if response.candidates:
            finish = getattr(response.candidates[0], "finish_reason", None)
        if finish and str(finish).upper() in ("MAX_TOKENS", "MAX_OUTPUT_TOKENS"):
            log.warning("gemini_output_truncated", model=model, finish_reason=str(finish))
        return text

    def _parse_structured(self, text: str, output_schema: type[T]) -> T:
        try:
            return output_schema.model_validate_json(text)
        except (ValidationError, json.JSONDecodeError):
            payload = parse_json_response(text)
            return output_schema.model_validate(payload)

    def structured(
        self,
        *,
        model: str,
        system: str,
        user: str,
        output_schema: type[T],
        max_tokens: int = 4096,
    ) -> T:
        from google.genai import types

        last_exc: Exception | None = None
        token_budget = max_tokens
        max_parse_attempts = 2 if self._settings.llm_conserve else 3

        for attempt in range(1, max_parse_attempts + 1):
            config = types.GenerateContentConfig(
                system_instruction=system,
                response_mime_type="application/json",
                response_schema=output_schema,
                max_output_tokens=token_budget,
                temperature=0.2,
            )
            try:
                text = self._generate(model=model, user=user, config=config)
            except GeminiQuotaExhaustedError:
                raise
            try:
                return self._parse_structured(text, output_schema)
            except Exception as exc:
                last_exc = exc
                if attempt < max_parse_attempts:
                    token_budget = min(int(token_budget * 1.5), 16384)
                    log.warning(
                        "structured_json_retry",
                        schema=output_schema.__name__,
                        model=model,
                        attempt=attempt,
                        len=len(text),
                        next_max_tokens=token_budget,
                        error=str(exc)[:200],
                    )
                    continue
                break

        raise RuntimeError(
            f"Gemini returned invalid JSON for {output_schema.__name__} "
            f"(model={model}, max_tokens={token_budget}): {last_exc}"
        ) from last_exc
