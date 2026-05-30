"""YAML → typed `Scenario`, with line-aware errors and the content-addressed id.

`spec` is otherwise pure: `load_scenario_file` is the *only* filesystem read in
the package, and exists purely so the CLI can hand us a path.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import ValidationError
from ruamel.yaml import YAML
from ruamel.yaml.error import MarkedYAMLError, YAMLError

from rangelab.common.errors import SpecError
from rangelab.common.ids import content_hash
from rangelab.spec.models import Scenario

# Round-trip mode (ruamel's default) keeps line/column info on loaded nodes so we
# can point authors at the offending key.
_yaml = YAML()


def load_scenario(text: str, *, source: str = "<string>") -> Scenario:
    """Parse YAML `text` into a validated `Scenario`, or raise `SpecError`."""
    try:
        data = _yaml.load(text)
    except YAMLError as exc:
        line: int | None = None
        problem: str | None = None
        if isinstance(exc, MarkedYAMLError):
            problem = exc.problem
            if exc.problem_mark is not None:
                line = exc.problem_mark.line + 1  # ruamel marks are 0-based
        where = f"line {line}" if line is not None else "unknown location"
        raise SpecError(
            f"could not parse YAML ({source})",
            code="spec.parse",
            hint=f"{where}: {problem or 'invalid YAML'}",
        ) from exc
    try:
        return Scenario.model_validate(data)
    except ValidationError as exc:
        raise _schema_error(exc, data, source) from exc


def load_scenario_file(path: str | Path) -> Scenario:
    """Read a scenario file and parse it — the only filesystem I/O in `spec`."""
    p = Path(path)
    return load_scenario(p.read_text(), source=str(p))


def canonicalize(scenario: Scenario) -> dict[str, Any]:
    """JSON-mode dump used as the content-hash input (declared field order)."""
    return scenario.model_dump(mode="json")


def compute_scenario_id(scenario: Scenario) -> str:
    """`sha256:` content hash of the canonical spec.

    `content_hash` sorts keys, so the id is invariant to YAML key order and to
    comments — the property the whole determinism story relies on.
    """
    return content_hash(canonicalize(scenario))


def _schema_error(exc: ValidationError, data: Any, source: str) -> SpecError:
    """Render pydantic errors with YAML line numbers where resolvable."""
    parts: list[str] = []
    for err in exc.errors():
        loc = err["loc"]
        where = ".".join(str(p) for p in loc) or "<root>"
        line = _line_of(data, loc)
        pos = f" (line {line})" if line is not None else ""
        parts.append(f"{where}{pos}: {err['msg']}")
    return SpecError(
        f"invalid scenario ({source})", code="spec.schema", hint="; ".join(parts)
    )


def _line_of(data: Any, loc: tuple[int | str, ...]) -> int | None:
    """1-based YAML line of the node at a pydantic-error `loc`, if resolvable."""
    parent: Any = None
    key: int | str | None = None
    node: Any = data
    for part in loc:
        parent, key = node, part
        try:
            node = node[part]
        except (KeyError, IndexError, TypeError):
            break
    # Fall back to the containing node's line for e.g. a *missing* key, whose own
    # position the YAML can't give us — "near here" still helps the author.
    return _line_of_key(parent, key) or _container_line(parent)


def _line_of_key(parent: Any, key: int | str | None) -> int | None:
    """Line of `key` within its ruamel container (`.lc`), or None if unavailable."""
    lc = getattr(parent, "lc", None)
    if lc is None or key is None:
        return None
    try:
        mark = lc.item(key) if isinstance(key, int) else lc.key(key)
    except (KeyError, IndexError, AttributeError, TypeError):
        return None
    return int(mark[0]) + 1 if mark else None


def _container_line(node: Any) -> int | None:
    """1-based start line of a ruamel container node, or None."""
    line = getattr(getattr(node, "lc", None), "line", None)
    return int(line) + 1 if line is not None else None
