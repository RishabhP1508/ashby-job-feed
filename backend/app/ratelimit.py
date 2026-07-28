"""A small in-memory rate limiter for auth endpoints.

It is per-process and per-IP: attempts are counted in a sliding window and reset
when the process restarts. That is enough to blunt password guessing on a single
instance. Across multiple instances, or for stronger guarantees, back this with
a shared store such as Redis.
"""
from __future__ import annotations

import time
from collections import defaultdict, deque
from threading import Lock

from fastapi import HTTPException


class RateLimiter:
    def __init__(self, max_attempts: int = 10, window_seconds: int = 300) -> None:
        self.max_attempts = max_attempts
        self.window_seconds = window_seconds
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def check(self, key: str) -> None:
        """Record an attempt for `key`; raise 429 if it exceeds the window limit."""
        now = time.monotonic()
        with self._lock:
            hits = self._hits[key]
            cutoff = now - self.window_seconds
            while hits and hits[0] < cutoff:
                hits.popleft()
            if len(hits) >= self.max_attempts:
                raise HTTPException(
                    status_code=429,
                    detail="Too many attempts. Please wait a few minutes and try again.",
                )
            hits.append(now)
