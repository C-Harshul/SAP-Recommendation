"""Exponential backoff for transient failures."""

from __future__ import annotations

from collections.abc import Callable
from typing import TypeVar

from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from ingestion.errors import SourceUnavailableError

T = TypeVar("T")

RETRY_WAIT = wait_exponential(multiplier=1, min=1, max=16)
RETRY_STOP = stop_after_attempt(4)


def with_retry(fn: Callable[[], T]) -> T:
    """Retry on SourceUnavailableError with 1s, 4s, 16s backoff."""

    @retry(
        retry=retry_if_exception_type(SourceUnavailableError),
        wait=RETRY_WAIT,
        stop=RETRY_STOP,
        reraise=True,
    )
    def _wrapped() -> T:
        return fn()

    return _wrapped()
