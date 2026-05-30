"""Minimal milestone & scoring models — Step 1.3 enriches these in place."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict


class Milestone(BaseModel):
    """A scored objective; `flags` reference FileArtifact.flag_id (checked in 1.2)."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str
    title: str
    flags: list[str] = []


class Scoring(BaseModel):
    """How milestone progress is credited (the semantics land in 1.3)."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    mode: Literal["sequential", "independent"] = "independent"
    partial_credit: bool = True
