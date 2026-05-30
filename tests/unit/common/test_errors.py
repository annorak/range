"""Error hierarchy: stable codes, str formatting, and RangeError ancestry."""

import pytest

from rangelab.common import (
    BackendError,
    ConfigError,
    ProvisionError,
    RangeError,
    RunError,
    ScoringError,
    SpecError,
    TraceError,
)

_SUBCLASSES = [
    (SpecError, "spec.error"),
    (ProvisionError, "provision.error"),
    (BackendError, "backend.error"),
    (TraceError, "trace.error"),
    (ScoringError, "scoring.error"),
    (RunError, "run.error"),
    (ConfigError, "config.error"),
]


@pytest.mark.parametrize(("cls", "code"), _SUBCLASSES)
def test_subclass_has_code_and_is_range_error(cls: type[RangeError], code: str) -> None:
    err = cls("boom")
    assert err.code == code
    assert isinstance(err, RangeError)


def test_base_code() -> None:
    assert RangeError("boom").code == "range.error"


def test_str_includes_code_and_hint() -> None:
    err = SpecError("bad spec", hint="fix line 3")
    assert str(err) == "[spec.error] bad spec — fix line 3"


def test_str_without_hint_omits_dash() -> None:
    err = SpecError("bad spec")
    assert str(err) == "[spec.error] bad spec"
    assert err.hint is None
    assert err.message == "bad spec"
