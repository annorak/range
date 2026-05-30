"""Correlation IDs and the content-hash helper — the join keys for the trace (§8)."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from typing import Any

from pydantic import BaseModel, ConfigDict
from ulid import ULID


def new_run_id() -> str:
    """A fresh `run_id` (ULID) — sortable by creation time."""
    return str(ULID())


def new_agent_id() -> str:
    """A fresh `agent_id` (ULID) — sortable by creation time."""
    return str(ULID())


def content_hash(obj: Mapping[str, Any] | str) -> str:
    """Stable `sha256:` hash of a JSON-canonicalizable mapping (or a raw string).

    For mappings the hash is invariant under key reordering — the property
    `scenario_id` relies on, so the `sort_keys` canonicalization must not change.
    """
    if isinstance(obj, str):
        payload = obj
    else:
        payload = json.dumps(obj, sort_keys=True, separators=(",", ":"))
    return "sha256:" + hashlib.sha256(payload.encode()).hexdigest()


class CorrelationIds(BaseModel):
    """The stable ID set tagged onto every log line and trace event (§8)."""

    model_config = ConfigDict(frozen=True)

    run_id: str
    scenario_id: str
    arm_id: str = "control"
    agent_id: str | None = None
    host_id: str | None = None
    step_seq: int = 0

    def as_log_context(self) -> dict[str, str | int]:
        """Non-null fields, for binding into structlog contextvars."""
        return {k: v for k, v in self.model_dump().items() if v is not None}
