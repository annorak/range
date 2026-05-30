"""IDs: ULID uniqueness/sortability, content-hash invariance, CorrelationIds."""

from hypothesis import given
from hypothesis import strategies as st

from rangelab.common import (
    CorrelationIds,
    content_hash,
    new_agent_id,
    new_run_id,
)


def test_run_ids_unique() -> None:
    ids = [new_run_id() for _ in range(1000)]
    assert len(set(ids)) == 1000


def test_run_ids_sort_by_creation_order() -> None:
    # The 48-bit timestamp prefix (first 10 chars of the 26-char ULID) is
    # monotonic by creation order; the random tail can reorder same-millisecond
    # IDs, so we assert ordering on the prefix only (the "allow same-ms ties").
    prefixes = [new_run_id()[:10] for _ in range(1000)]
    assert prefixes == sorted(prefixes)


def test_agent_id_is_a_distinct_ulid() -> None:
    assert new_agent_id() != new_agent_id()


def test_content_hash_invariant_under_key_order() -> None:
    a = {"b": 1, "a": 2, "c": 3}
    b = {"c": 3, "a": 2, "b": 1}
    assert content_hash(a) == content_hash(b)


def test_content_hash_differs_for_different_content() -> None:
    assert content_hash({"a": 1}) != content_hash({"a": 2})


def test_content_hash_of_string() -> None:
    h = content_hash("hello")
    assert h.startswith("sha256:")
    assert content_hash("hello") == h
    assert content_hash("hello") != content_hash("world")


@given(
    st.dictionaries(
        st.text(min_size=1, max_size=8),
        st.integers(),
        min_size=1,
        max_size=8,
    )
)
def test_content_hash_invariant_under_permutation(data: dict[str, int]) -> None:
    permuted = dict(reversed(list(data.items())))
    assert content_hash(data) == content_hash(permuted)


def test_correlation_ids_as_log_context_drops_nulls() -> None:
    ids = CorrelationIds(run_id="r1", scenario_id="s1")
    ctx = ids.as_log_context()
    assert ctx == {
        "run_id": "r1",
        "scenario_id": "s1",
        "arm_id": "control",
        "step_seq": 0,
    }
    assert "agent_id" not in ctx
    assert "host_id" not in ctx


def test_correlation_ids_include_optional_fields_when_set() -> None:
    ids = CorrelationIds(
        run_id="r1",
        scenario_id="s1",
        agent_id="a1",
        host_id="h1",
        step_seq=4,
    )
    assert ids.as_log_context() == {
        "run_id": "r1",
        "scenario_id": "s1",
        "arm_id": "control",
        "agent_id": "a1",
        "host_id": "h1",
        "step_seq": 4,
    }


def test_correlation_ids_are_frozen() -> None:
    ids = CorrelationIds(run_id="r1", scenario_id="s1")
    try:
        ids.run_id = "r2"  # type: ignore[misc]
    except Exception as exc:  # frozen model raises on mutation
        assert "frozen" in str(exc).lower() or "Instance is frozen" in str(exc)
    else:
        raise AssertionError("CorrelationIds should be frozen")
