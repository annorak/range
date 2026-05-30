"""Model-level invariants: structural validators, extra-forbid, frozen, defaults."""

import pytest
from pydantic import ValidationError

from rangelab.spec import (
    FileArtifact,
    Host,
    Metadata,
    Network,
    Resources,
    Scenario,
    Subnet,
)


def test_file_artifact_content_only_ok() -> None:
    f = FileArtifact(path="/etc/motd", content="hello")
    assert f.content_ref is None and f.mode == "0644"


def test_file_artifact_flag_with_ref_ok() -> None:
    f = FileArtifact(
        path="/flag", content_ref="artifacts/flag.txt", is_flag=True, flag_id="f1"
    )
    assert f.is_flag and f.flag_id == "f1"


def test_file_artifact_rejects_both_sources() -> None:
    with pytest.raises(ValidationError, match="exactly one of"):
        FileArtifact(path="/x", content="a", content_ref="b")


def test_file_artifact_rejects_neither_source() -> None:
    with pytest.raises(ValidationError, match="exactly one of"):
        FileArtifact(path="/x")


def test_flag_requires_flag_id() -> None:
    with pytest.raises(ValidationError, match="requires 'flag_id'"):
        FileArtifact(path="/flag", content="x", is_flag=True)


def test_extra_field_forbidden() -> None:
    with pytest.raises(ValidationError):
        Metadata(name="x", bogus="nope")  # type: ignore[call-arg]


def test_models_are_frozen() -> None:
    m = Metadata(name="x")
    with pytest.raises(ValidationError):
        m.name = "y"  # type: ignore[misc]


def test_resources_defaults() -> None:
    r = Resources()
    assert (r.cpu, r.memory_mb) == (0.5, 512)


def test_host_minimal_defaults() -> None:
    h = Host(name="web", subnet="dmz", image="img@sha256:abc", role="entry")
    assert h.services == [] and h.files == [] and h.resources == Resources()


def test_minimal_scenario_builds() -> None:
    s = Scenario(
        apiVersion="range/v1alpha1",
        metadata=Metadata(name="x"),
        network=Network(subnets=[Subnet(name="dmz", cidr="10.0.0.0/24")]),
        hosts=[Host(name="h", subnet="dmz", image="i@sha256:1", role="target")],
    )
    assert s.defenses is None and s.identities == [] and s.scoring.mode == "independent"
