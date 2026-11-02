import time
import threading
from collections import defaultdict, deque

from fastapi import HTTPException, status


class RateLimiter:
    """Best-effort sliding-window limiter (per process; serverless instances don't share state)."""

    def __init__(self, max_attempts: int, window_seconds: int):
        self.max_attempts = max_attempts
        self.window = window_seconds
        self._hits = defaultdict(deque)
        self._lock = threading.Lock()

    def check(self, key: str) -> None:
        now = time.monotonic()
        with self._lock:
            q = self._hits[key]
            while q and now - q[0] > self.window:
                q.popleft()
            if len(q) >= self.max_attempts:
                retry = int(self.window - (now - q[0])) + 1
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Terlalu banyak percobaan. Coba lagi dalam {retry} detik.",
                    headers={"Retry-After": str(retry)},
                )

    def hit(self, key: str) -> None:
        with self._lock:
            self._hits[key].append(time.monotonic())

    def reset(self, key: str) -> None:
        with self._lock:
            self._hits.pop(key, None)


login_limiter = RateLimiter(max_attempts=8, window_seconds=300)
recovery_limiter = RateLimiter(max_attempts=5, window_seconds=900)
