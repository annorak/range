"""UTC clock and the hybrid logical clock that orders the unified timeline (§8)."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime


def utc_now() -> datetime:
    """Current time as a tz-aware UTC datetime."""
    return datetime.now(UTC)


@dataclass(slots=True, frozen=True, order=True)
class HybridTimestamp:
    """A point on the one timeline: wall clock plus deterministic counters.

    Ordering is by `(step_seq, source_seq)` only — `wall` is `compare=False`
    because wall clocks can skew or collide across sources, so the counters,
    not the clock, are the authoritative deterministic order (§8).
    """

    wall: datetime = field(compare=False)
    step_seq: int
    source_seq: int


class LogicalClock:
    """Monotonic per-process clock producing `(wall, step_seq, source_seq)`.

    Seedable for tests via `now_fn`. `tick()` advances the step; `sub()` advances
    within the current step. The `(step_seq, source_seq)` pair is strictly
    increasing even if `wall` goes backwards.
    """

    def __init__(self, now_fn: Callable[[], datetime] = utc_now) -> None:
        self._now_fn = now_fn
        self._step_seq = 0
        self._source_seq = 0

    def tick(self) -> HybridTimestamp:
        """Advance to the next step (`step_seq += 1`, `source_seq` reset to 0)."""
        self._step_seq += 1
        self._source_seq = 0
        return HybridTimestamp(self._now_fn(), self._step_seq, self._source_seq)

    def sub(self) -> HybridTimestamp:
        """Advance within the current step (`source_seq += 1`)."""
        self._source_seq += 1
        return HybridTimestamp(self._now_fn(), self._step_seq, self._source_seq)
