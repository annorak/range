"""structlog setup: renderers, secret redaction, and correlation-ID binding.

`configure_logging` takes the two rendering knobs it needs as scalars rather than
a `Settings` object: `config` sits above `common` in the import layering (ADR
0002/0003), so `common` cannot import `config`. Callers pass the values down.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Literal

import structlog
from structlog.typing import EventDict, Processor, WrappedLogger

from rangelab.common.ids import CorrelationIds

_REDACTED = "***REDACTED***"

# A small, named safety net — not a vault. Each pattern matches a known key shape;
# matched substrings are scrubbed before any renderer sees them.
_SECRET_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"sk-[A-Za-z0-9_-]{8,}"),  # OpenAI-style API keys
    re.compile(r"AKIA[0-9A-Z]{16}"),  # AWS access key IDs
    re.compile(r"Bearer\s+\S+"),  # bearer auth tokens
    re.compile(r"eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+"),  # JWT-ish
)


def _redact_value(value: Any) -> Any:
    """Scrub secret-shaped substrings, recursing into dicts and lists."""
    if isinstance(value, str):
        for pattern in _SECRET_PATTERNS:
            value = pattern.sub(_REDACTED, value)
        return value
    if isinstance(value, dict):
        return {k: _redact_value(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_redact_value(v) for v in value]
    return value


def _redact_secrets(
    logger: WrappedLogger, method_name: str, event_dict: EventDict
) -> EventDict:
    """structlog processor: redact known secret shapes from every event value."""
    for key, value in event_dict.items():
        event_dict[key] = _redact_value(value)
    return event_dict


def configure_logging(
    *, log_format: Literal["console", "json"], log_level: str = "INFO"
) -> None:
    """Configure structlog process-wide: contextvars, timestamp, redaction, render."""
    renderer: Processor = (
        structlog.processors.JSONRenderer()
        if log_format == "json"
        else structlog.dev.ConsoleRenderer()
    )
    level_no = logging.getLevelNamesMapping().get(log_level.upper(), logging.INFO)
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            _redact_secrets,
            renderer,
        ],
        wrapper_class=structlog.make_filtering_bound_logger(level_no),
        logger_factory=structlog.PrintLoggerFactory(),
        # Don't cache: re-`configure` (CLI profile switch, tests) must take effect.
        cache_logger_on_first_use=False,
    )


def get_logger(name: str | None = None) -> structlog.BoundLogger:
    """A bound logger; correlation IDs bound via `bind_correlation` auto-attach."""
    logger: structlog.BoundLogger = (
        structlog.get_logger() if name is None else structlog.get_logger(name)
    )
    return logger


def bind_correlation(ids: CorrelationIds) -> None:
    """Bind correlation IDs so later log lines on this context carry them."""
    structlog.contextvars.bind_contextvars(**ids.as_log_context())


def clear_correlation() -> None:
    """Clear any correlation IDs bound on the current context."""
    structlog.contextvars.clear_contextvars()
