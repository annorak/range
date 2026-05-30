"""JSON Schema export of the scenario models, for editor/LSP tooling."""

from __future__ import annotations

from typing import Any

from rangelab.spec.models import Scenario


def export_json_schema() -> dict[str, Any]:
    """The `Scenario` JSON Schema (as produced by Pydantic v2) as a dict."""
    return Scenario.model_json_schema()
