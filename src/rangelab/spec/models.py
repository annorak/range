"""The Pydantic model tree for a Range scenario — the spine of the system."""

from __future__ import annotations

from typing import Any, Literal, Self

from pydantic import BaseModel, ConfigDict, model_validator

from rangelab.spec.milestones import Milestone, Scoring

Role = Literal["entry", "server", "workstation", "router", "target"]


class SpecModel(BaseModel):
    """Base for every spec model: typo-proof (`extra` forbidden) and immutable."""

    # extra="forbid" turns author typos into errors; frozen keeps specs immutable
    # (good for determinism; 1.3's fragment merge builds *new* instances).
    model_config = ConfigDict(extra="forbid", frozen=True)


class Metadata(SpecModel):
    name: str
    description: str | None = None
    labels: dict[str, str] = {}


class Subnet(SpecModel):
    name: str
    cidr: str  # validated as a plain string here; CIDR math is Step 1.2


class Network(SpecModel):
    subnets: list[Subnet]


class Resources(SpecModel):
    cpu: float = 0.5
    memory_mb: int = 512


class Service(SpecModel):
    name: str
    type: str
    port: int
    config: dict[str, Any] = {}


class FileArtifact(SpecModel):
    path: str
    content: str | None = None
    content_ref: str | None = None  # indirection; never inline a secret
    mode: str = "0644"
    is_flag: bool = False
    flag_id: str | None = None

    @model_validator(mode="after")
    def _exactly_one_source(self) -> Self:
        # Exactly one content source: keep the spec a single source of truth so
        # `content_ref` stays an indirection (no real secret/blob inlined).
        if (self.content is None) == (self.content_ref is None):
            raise ValueError("exactly one of 'content' or 'content_ref' is required")
        if self.is_flag and self.flag_id is None:
            raise ValueError("a flag file ('is_flag: true') requires 'flag_id'")
        return self


class Host(SpecModel):
    name: str
    subnet: str  # references Subnet.name (checked in 1.2)
    image: str  # digest-pinned (enforced in 1.2)
    role: Role
    services: list[Service] = []
    files: list[FileArtifact] = []
    env: dict[str, str] = {}
    resources: Resources = Resources()


class Identity(SpecModel):
    username: str
    secret_ref: str  # indirection — never an inline secret
    locations: list[str] = []  # host names (checked in 1.2)


class Defense(SpecModel):  # minimal in v1.1; expanded in Epic 6
    name: str
    type: str
    config: dict[str, Any] = {}


class Scenario(SpecModel):
    apiVersion: Literal["range/v1alpha1"]
    metadata: Metadata
    network: Network
    hosts: list[Host]
    identities: list[Identity] = []
    defenses: list[Defense] | None = None
    milestones: list[Milestone] = []
    scoring: Scoring = Scoring()
