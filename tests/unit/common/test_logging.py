"""Logging: secret redaction, correlation binding, and SecretStr safety."""

from collections.abc import Iterator

import pytest
from pydantic import SecretStr

from rangelab.common import (
    CorrelationIds,
    bind_correlation,
    clear_correlation,
    configure_logging,
    get_logger,
)
from rangelab.common.logging import _redact_secrets, _redact_value


@pytest.fixture(autouse=True)
def _clean_context() -> Iterator[None]:
    clear_correlation()
    yield
    clear_correlation()


# --- redaction processor (unit) -------------------------------------------------


def test_redacts_openai_key() -> None:
    out = _redact_value("key is sk-abcdef0123456789")
    assert "sk-abcdef" not in out
    assert "***REDACTED***" in out


def test_redacts_aws_key() -> None:
    assert _redact_value("AKIAIOSFODNN7EXAMPLE") == "***REDACTED***"


def test_redacts_bearer_token() -> None:
    assert _redact_value("Bearer abc.def.ghi") == "***REDACTED***"


def test_redacts_jwt() -> None:
    jwt = "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjMifQ.SflKxwRJSMeKKF2QT4"
    assert _redact_value(jwt) == "***REDACTED***"


def test_redaction_recurses_into_dict_and_list() -> None:
    event = _redact_secrets(
        None,
        "info",
        {
            "nested": {"token": "Bearer secret-value"},
            "items": ["AKIAIOSFODNN7EXAMPLE", "clean"],
            "count": 7,
        },
    )
    assert event["nested"]["token"] == "***REDACTED***"
    assert event["items"] == ["***REDACTED***", "clean"]
    assert event["count"] == 7  # non-string values pass through untouched


# --- end-to-end through configure_logging --------------------------------------


def test_console_redacts_in_rendered_output(capsys: pytest.CaptureFixture[str]) -> None:
    configure_logging(log_format="console")
    get_logger().info("call", api_key="sk-abcdef0123456789")
    out = capsys.readouterr().out
    assert "***REDACTED***" in out
    assert "sk-abcdef" not in out


def test_bound_correlation_ids_appear_then_clear(
    capsys: pytest.CaptureFixture[str],
) -> None:
    configure_logging(log_format="console")
    bind_correlation(CorrelationIds(run_id="run-xyz", scenario_id="scn-1"))
    get_logger().info("first")
    bound = capsys.readouterr().out
    assert "run-xyz" in bound
    assert "scn-1" in bound

    clear_correlation()
    get_logger().info("second")
    after = capsys.readouterr().out
    assert "run-xyz" not in after


def test_secretstr_value_not_rendered(capsys: pytest.CaptureFixture[str]) -> None:
    configure_logging(log_format="console")
    get_logger().info("auth", key=SecretStr("topsecret"))
    out = capsys.readouterr().out
    assert "topsecret" not in out


def test_json_format_renders_and_redacts(
    capsys: pytest.CaptureFixture[str],
) -> None:
    configure_logging(log_format="json")
    get_logger("svc").info("event", token="sk-abcdef0123456789")
    out = capsys.readouterr().out
    assert '"event": "event"' in out
    assert "***REDACTED***" in out
    assert "sk-abcdef" not in out


def test_log_level_filters_below_threshold(
    capsys: pytest.CaptureFixture[str],
) -> None:
    configure_logging(log_format="console", log_level="WARNING")
    log = get_logger()
    log.info("suppressed")
    log.warning("shown")
    out = capsys.readouterr().out
    assert "suppressed" not in out
    assert "shown" in out
