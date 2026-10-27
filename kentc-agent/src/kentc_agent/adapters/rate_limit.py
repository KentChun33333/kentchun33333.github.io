"""Process-local rolling admission estimates; provider token counters remain authoritative."""

from __future__ import annotations

import math
import threading
import time
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass
from email.utils import parsedate_to_datetime


class RateLimitExceeded(RuntimeError):
    """Admission cannot finish within this call's configured rate-wait allowance."""


@dataclass
class _Reservation:
    started: float
    tokens: int
    active: bool = True


class RateWait:
    """One wait allowance shared across admission, HTTP retries and backend failover."""

    def __init__(self, maximum: float, clock: Callable[[], float], sleep: Callable[[float], None]) -> None:
        self.maximum = maximum
        self.spent = 0.0
        self._clock = clock
        self._sleep = sleep

    def wait(self, seconds: float) -> None:
        if seconds <= 0:
            return
        remaining = max(0.0, self.maximum - self.spent)
        if seconds > remaining:
            raise RateLimitExceeded(
                f"rate-limit wait requires {seconds:.3f}s but only {remaining:.3f}s remains "
                f"of rate_limit_max_wait={self.maximum:g}s"
            )
        before = self._clock()
        self._sleep(seconds)  # No limiter lock; KeyboardInterrupt/cancellation propagates normally.
        self.spent += max(seconds, self._clock() - before)


class RollingTokenBudget:
    """Concurrency-safe 60-second reservations shared by one client and its fallback.

    Unknown/failed requests retain their reservation until expiry. Only a successful
    response with reported usage reconciles the estimate. No network or sleep runs
    while the accounting lock is held. A zero quota disables token admission, not
    shared provider cooldowns.
    """

    WINDOW = 60.0

    def __init__(self, tokens_per_minute: int, max_wait: float, *,
                 clock: Callable[[], float] | None = None,
                 sleep: Callable[[float], None] | None = None) -> None:
        if isinstance(tokens_per_minute, bool) or not isinstance(tokens_per_minute, int) or tokens_per_minute < 0:
            raise ValueError("tokens_per_minute must be a non-negative integer (0 disables admission)")
        if isinstance(max_wait, bool) or not math.isfinite(max_wait) or max_wait < 0:
            raise ValueError("rate_limit_max_wait must be finite and non-negative")
        self.limit = tokens_per_minute
        self.max_wait = max_wait
        self._clock = clock or time.monotonic
        self._sleep = sleep or time.sleep
        self._lock = threading.Lock()
        self._reservations: deque[_Reservation] = deque()
        self._tokens = 0
        self._cooldown_until = 0.0

    def new_wait(self) -> RateWait:
        return RateWait(self.max_wait, self._clock, self._sleep)

    def _expire(self, now: float) -> None:
        while self._reservations and self._reservations[0].started + self.WINDOW <= now:
            old = self._reservations.popleft()
            old.active = False
            self._tokens -= old.tokens

    def reserve(self, tokens: int, waiting: RateWait) -> _Reservation | None:
        if self.limit and tokens > self.limit:
            raise RateLimitExceeded(
                f"request reservation of approximately {tokens:,} tokens exceeds "
                f"tokens_per_minute={self.limit:,}; lower the prompt/output budget or raise the configured quota"
            )
        while True:
            with self._lock:
                now = self._clock()
                self._expire(now)
                delay = max(0.0, self._cooldown_until - now)
                if self.limit and self._tokens + tokens > self.limit:
                    released = 0
                    for reservation in self._reservations:
                        released += reservation.tokens
                        if self._tokens - released + tokens <= self.limit:
                            delay = max(delay, reservation.started + self.WINDOW - now)
                            break
                if delay <= 0:
                    if not self.limit:
                        return None
                    reservation = _Reservation(now, tokens)
                    self._reservations.append(reservation)
                    self._tokens += tokens
                    return reservation
            waiting.wait(delay)

    def reconcile(self, reservation: _Reservation | None, actual_tokens: int) -> None:
        if reservation is None:
            return
        with self._lock:
            self._expire(self._clock())
            if reservation.active:
                self._tokens += actual_tokens - reservation.tokens
                reservation.tokens = actual_tokens

    def defer(self, seconds: float) -> None:
        """Make a provider Retry-After/backoff visible to every concurrent caller."""
        with self._lock:
            self._cooldown_until = max(self._cooldown_until, self._clock() + seconds)


def retry_after(value: str | None, *, now: float | None = None) -> float | None:
    """Parse Retry-After delta seconds or an HTTP date; invalid values use backoff."""
    if value is None:
        return None
    try:
        seconds = float(value)
    except (TypeError, ValueError):
        try:
            date = parsedate_to_datetime(value)
            seconds = date.timestamp() - (time.time() if now is None else now)
        except (TypeError, ValueError, OverflowError):
            return None
    return max(0.0, seconds) if math.isfinite(seconds) else None
