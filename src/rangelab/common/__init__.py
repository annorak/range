"""Shared substrate: correlation IDs, errors, time/clock, and logging."""

from rangelab.common.errors import (
    BackendError,
    ConfigError,
    ProvisionError,
    RangeError,
    RunError,
    ScoringError,
    SpecError,
    TraceError,
)
from rangelab.common.ids import (
    CorrelationIds,
    content_hash,
    new_agent_id,
    new_run_id,
)
from rangelab.common.logging import (
    bind_correlation,
    clear_correlation,
    configure_logging,
    get_logger,
)
from rangelab.common.time import HybridTimestamp, LogicalClock, utc_now

__all__ = [
    "BackendError",
    "ConfigError",
    "CorrelationIds",
    "HybridTimestamp",
    "LogicalClock",
    "ProvisionError",
    "RangeError",
    "RunError",
    "ScoringError",
    "SpecError",
    "TraceError",
    "bind_correlation",
    "clear_correlation",
    "configure_logging",
    "content_hash",
    "get_logger",
    "new_agent_id",
    "new_run_id",
    "utc_now",
]
