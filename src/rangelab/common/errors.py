"""The Range error hierarchy: a typed root with a stable code and optional hint."""

from __future__ import annotations


class RangeError(Exception):
    """Base for all Range errors. Carries a stable `code` and optional `hint`."""

    code: str = "range.error"  # subclasses override

    def __init__(self, message: str, *, hint: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.hint = hint

    def __str__(self) -> str:
        return f"[{self.code}] {self.message}" + (
            f" — {self.hint}" if self.hint else ""
        )


class SpecError(RangeError):
    """Invalid or unparseable scenario spec."""

    code = "spec.error"


class ProvisionError(RangeError):
    """A range failed to provision."""

    code = "provision.error"


class BackendError(RangeError):
    """A provisioner backend operation failed."""

    code = "backend.error"


class TraceError(RangeError):
    """A trace capture, store, or query operation failed."""

    code = "trace.error"


class ScoringError(RangeError):
    """Scoring a run against its milestones failed."""

    code = "scoring.error"


class RunError(RangeError):
    """A run could not be completed."""

    code = "run.error"


class ConfigError(RangeError):
    """Invalid or missing configuration."""

    code = "config.error"
