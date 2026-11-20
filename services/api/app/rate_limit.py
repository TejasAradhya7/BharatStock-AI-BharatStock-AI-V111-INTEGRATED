"""Small per-process sliding-window limiter for expensive public API routes.

For multi-worker or multi-replica production deployments, replace this in-memory
store with a shared Redis limiter so quotas are consistent across processes.
"""
from __future__ import annotations

import threading
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Callable


@dataclass
class SlidingWindowLimiter:
    clock: Callable[[], float] = time.monotonic
    _events: dict[tuple[str, str], deque[float]] = field(default_factory=dict)
    _lock: threading.Lock = field(default_factory=threading.Lock)

    def check(self, key: str, bucket: str, limit: int, window_seconds: int) -> tuple[bool, int]:
        """Return (allowed, retry_after_seconds) and record allowed attempts."""
        now = self.clock()
        limit = max(1, int(limit))
        window = max(1, int(window_seconds))
        event_key = (key, bucket)
        with self._lock:
            events = self._events.setdefault(event_key, deque())
            cutoff = now - window
            while events and events[0] <= cutoff:
                events.popleft()
            if len(events) >= limit:
                retry_after = max(1, int(events[0] + window - now + 0.999))
                return False, retry_after
            events.append(now)
            # Opportunistic cleanup prevents dead client keys accumulating forever.
            if len(self._events) > 5000:
                expired_keys = [k for k, q in self._events.items() if not q or q[-1] <= cutoff]
                for expired_key in expired_keys[:1000]:
                    self._events.pop(expired_key, None)
            return True, 0

    def clear(self) -> None:
        with self._lock:
            self._events.clear()


limiter = SlidingWindowLimiter()
