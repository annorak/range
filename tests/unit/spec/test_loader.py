"""Loader: reference parse, round-trip stability, scenario_id invariance, errors."""

import string
from io import StringIO
from pathlib import Path
from typing import Any

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from ruamel.yaml import YAML

from rangelab.common import SpecError, content_hash
from rangelab.spec import (
    Host,
    Metadata,
    Network,
    Scenario,
    Subnet,
    canonicalize,
    compute_scenario_id,
    load_scenario,
    load_scenario_file,
)
from rangelab.spec.loader import _line_of, _line_of_key

_HERE = Path(__file__).parent
_DATA = _HERE / "data"
_EXAMPLE = _HERE.parents[2] / "examples" / "scenarios" / "mini-enterprise.yaml"

_yaml = YAML()


def _to_yaml(obj: dict[str, Any]) -> str:
    buf = StringIO()
    _yaml.dump(obj, buf)
    return buf.getvalue()


def _shuffle_keys(obj: Any) -> Any:
    """Recursively reverse dict insertion order — same content, different order."""
    if isinstance(obj, dict):
        return {k: _shuffle_keys(v) for k, v in reversed(list(obj.items()))}
    if isinstance(obj, list):
        return [_shuffle_keys(v) for v in obj]
    return obj


# --- reference parse --------------------------------------------------------


def test_loads_reference_scenario() -> None:
    s = load_scenario_file(_EXAMPLE)
    assert [h.name for h in s.hosts] == ["edge-router", "web", "app-db", "analyst-ws"]
    assert {h.role for h in s.hosts} == {"router", "entry", "server", "workstation"}
    flags = [f for h in s.hosts for f in h.files if f.is_flag]
    assert [f.flag_id for f in flags] == ["flag-db-creds"]
    assert s.scoring.mode == "sequential"


# --- round-trip + id invariance --------------------------------------------


def test_round_trip_identity() -> None:
    s = load_scenario_file(_EXAMPLE)
    again = load_scenario(_to_yaml(canonicalize(s)))
    assert again == s
    assert compute_scenario_id(again) == compute_scenario_id(s)


def test_scenario_id_invariant_under_key_order() -> None:
    s = load_scenario_file(_EXAMPLE)
    canon = canonicalize(s)
    assert content_hash(_shuffle_keys(canon)) == content_hash(canon)


def test_scenario_id_invariant_under_comments() -> None:
    s1 = load_scenario_file(_EXAMPLE)
    text = _EXAMPLE.read_text()
    commented = "# a leading comment\n" + text.replace(
        "role: entry", "role: entry  # the DMZ entrypoint"
    )
    s2 = load_scenario(commented)
    assert compute_scenario_id(s2) == compute_scenario_id(s1)


# --- error paths ------------------------------------------------------------


def test_malformed_yaml_is_parse_error() -> None:
    with pytest.raises(SpecError) as exc:
        load_scenario_file(_DATA / "broken_yaml.yaml")
    assert exc.value.code == "spec.parse"
    assert exc.value.hint is not None and "line" in exc.value.hint


def test_unknown_field_is_schema_error() -> None:
    with pytest.raises(SpecError) as exc:
        load_scenario_file(_DATA / "broken_extra_field.yaml")
    assert exc.value.code == "spec.schema"
    assert exc.value.hint is not None and "bogus_field" in exc.value.hint


def test_missing_field_schema_error_reports_line() -> None:
    text = (
        "apiVersion: range/v1alpha1\n"
        "metadata:\n"
        "  name: x\n"
        "network:\n"
        "  subnets:\n"
        "    - name: dmz\n"
        "      cidr: 10.0.0.0/24\n"
        "hosts:\n"
        "  - name: web\n"  # missing required `image`
        "    subnet: dmz\n"
        "    role: entry\n"
    )
    with pytest.raises(SpecError) as exc:
        load_scenario(text)
    assert exc.value.code == "spec.schema"
    assert exc.value.hint is not None and "line" in exc.value.hint


def test_schema_error_resolves_list_item_line() -> None:
    # A scalar where a Subnet mapping is expected: the error `loc` ends in an int
    # index, exercising the list-item line resolution path.
    text = (
        "apiVersion: range/v1alpha1\n"
        "metadata:\n"
        "  name: x\n"
        "network:\n"
        "  subnets:\n"
        "    - not-a-mapping\n"
        "hosts: []\n"
    )
    with pytest.raises(SpecError) as exc:
        load_scenario(text)
    assert exc.value.code == "spec.schema"
    assert exc.value.hint is not None and "line" in exc.value.hint


def test_structural_validator_surfaces_as_schema_error() -> None:
    text = (
        "apiVersion: range/v1alpha1\n"
        "metadata:\n"
        "  name: x\n"
        "network:\n"
        "  subnets:\n"
        "    - name: dmz\n"
        "      cidr: 10.0.0.0/24\n"
        "hosts:\n"
        "  - name: web\n"
        "    subnet: dmz\n"
        "    image: i@sha256:1\n"
        "    role: entry\n"
        "    files:\n"
        "      - path: /x\n"
        "        content: a\n"
        "        content_ref: b\n"  # both sources → structural validator trips
    )
    with pytest.raises(SpecError) as exc:
        load_scenario(text)
    assert exc.value.code == "spec.schema"


# --- private line-resolution branches --------------------------------------


def test_line_of_handles_unsubscriptable_node() -> None:
    assert _line_of(None, ("a",)) is None


def test_line_of_key_without_lc_is_none() -> None:
    assert _line_of_key({}, "x") is None
    assert _line_of_key(None, None) is None


def test_line_of_key_missing_key_is_none() -> None:
    data = _yaml.load("a: 1\n")
    assert _line_of_key(data, "missing") is None


# --- property: random valid specs round-trip & hash stably ------------------

_word = st.text(alphabet=string.ascii_lowercase, min_size=1, max_size=6)
_role = st.sampled_from(["entry", "server", "workstation", "router", "target"])


@st.composite
def scenarios(draw: st.DrawFn) -> Scenario:
    subnet_names = draw(st.lists(_word, min_size=1, max_size=3, unique=True))
    subnets = [
        Subnet(name=n, cidr=f"10.0.{i}.0/24") for i, n in enumerate(subnet_names)
    ]
    n_hosts = draw(st.integers(min_value=1, max_value=4))
    hosts = [
        Host(
            name=f"h{i}",
            subnet=draw(st.sampled_from(subnet_names)),
            image="img@sha256:" + "0" * 64,
            role=draw(_role),
        )
        for i in range(n_hosts)
    ]
    return Scenario(
        apiVersion="range/v1alpha1",
        metadata=Metadata(name=draw(_word)),
        network=Network(subnets=subnets),
        hosts=hosts,
    )


@settings(deadline=None, max_examples=50)
@given(scenarios())
def test_random_scenarios_round_trip(s: Scenario) -> None:
    again = load_scenario(_to_yaml(canonicalize(s)))
    assert again == s
    assert compute_scenario_id(again) == compute_scenario_id(s)


@settings(deadline=None, max_examples=50)
@given(scenarios())
def test_random_scenario_id_invariant_under_key_order(s: Scenario) -> None:
    canon = canonicalize(s)
    assert content_hash(_shuffle_keys(canon)) == content_hash(canon)
