"""Clock: utc_now tz-awareness, counter monotonicity, counter-not-wall ordering."""

from datetime import UTC, datetime, timedelta

from rangelab.common import HybridTimestamp, LogicalClock, utc_now


def test_utc_now_is_tz_aware_utc() -> None:
    now = utc_now()
    assert now.tzinfo == UTC


def test_tick_resets_source_seq_and_advances_step() -> None:
    clock = LogicalClock()
    t1 = clock.tick()
    s1 = clock.sub()
    t2 = clock.tick()
    assert (t1.step_seq, t1.source_seq) == (1, 0)
    assert (s1.step_seq, s1.source_seq) == (1, 1)
    assert (t2.step_seq, t2.source_seq) == (2, 0)


def test_counters_strictly_increase_even_with_backwards_clock() -> None:
    # now_fn marches backwards; the (step_seq, source_seq) order must still hold.
    base = datetime(2026, 1, 1, tzinfo=UTC)
    ticks = iter(range(100))
    clock = LogicalClock(now_fn=lambda: base - timedelta(seconds=next(ticks)))

    stamps = []
    for _ in range(10):
        stamps.append(clock.tick())
        stamps.append(clock.sub())
        stamps.append(clock.sub())

    keys = [(s.step_seq, s.source_seq) for s in stamps]
    assert keys == sorted(keys)
    assert len(set(keys)) == len(keys)  # strictly increasing => all distinct
    assert stamps == sorted(stamps)  # ordering ignores the backwards wall clock


def test_deterministic_under_seeded_now_fn() -> None:
    fixed = datetime(2026, 5, 29, 12, 0, tzinfo=UTC)
    clock = LogicalClock(now_fn=lambda: fixed)
    t = clock.tick()
    assert t == HybridTimestamp(fixed, 1, 0)
    assert t.wall == fixed


def test_hybrid_timestamp_sorts_by_counters_not_wall() -> None:
    early_wall = datetime(2026, 1, 1, tzinfo=UTC)
    late_wall = datetime(2026, 12, 31, tzinfo=UTC)
    # Later wall clock but earlier counters must sort first.
    a = HybridTimestamp(late_wall, step_seq=1, source_seq=0)
    b = HybridTimestamp(early_wall, step_seq=2, source_seq=0)
    assert sorted([b, a]) == [a, b]


def test_hybrid_timestamp_equal_on_counters_ignores_wall() -> None:
    w1 = datetime(2026, 1, 1, tzinfo=UTC)
    w2 = datetime(2026, 6, 1, tzinfo=UTC)
    assert HybridTimestamp(w1, 1, 0) == HybridTimestamp(w2, 1, 0)
