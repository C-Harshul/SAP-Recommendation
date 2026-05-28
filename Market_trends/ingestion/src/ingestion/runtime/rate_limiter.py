"""Token-bucket rate limiter per source_id."""

from __future__ import annotations

import threading
import time


class TokenBucket:
    """Simple token bucket for request pacing."""

    def __init__(self, rate_per_second: float, capacity: float | None = None) -> None:
        self.rate = rate_per_second
        self.capacity = capacity if capacity is not None else max(rate_per_second, 1.0)
        self.tokens = self.capacity
        self.updated_at = time.monotonic()
        self._lock = threading.Lock()

    def acquire(self, tokens: float = 1.0) -> None:
        with self._lock:
            now = time.monotonic()
            elapsed = now - self.updated_at
            self.updated_at = now
            self.tokens = min(self.capacity, self.tokens + elapsed * self.rate)
            if self.tokens < tokens:
                sleep_for = (tokens - self.tokens) / self.rate
                time.sleep(sleep_for)
                self.tokens = 0.0
            else:
                self.tokens -= tokens


class RateLimiterRegistry:
    """One bucket per source_id."""

    def __init__(self) -> None:
        self._buckets: dict[str, TokenBucket] = {}
        self._lock = threading.Lock()

    def get(self, source_id: str, requests_per_minute: float = 30.0) -> TokenBucket:
        with self._lock:
            if source_id not in self._buckets:
                rps = max(requests_per_minute / 60.0, 0.1)
                self._buckets[source_id] = TokenBucket(rate_per_second=rps)
            return self._buckets[source_id]
