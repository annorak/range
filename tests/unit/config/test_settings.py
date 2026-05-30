"""Settings: load precedence, prod log-format flip, and SecretStr masking."""

from pathlib import Path

import pytest

from rangelab.config import Settings, get_settings


@pytest.fixture(autouse=True)
def _clear_range_env(monkeypatch: pytest.MonkeyPatch) -> None:
    # Tests own the environment; strip any RANGE_* that leaked in from the shell.
    for key in ("RANGE_CONFIG", "RANGE_LOG_LEVEL", "RANGE_PROFILE", "RANGE_LOG_FORMAT"):
        monkeypatch.delenv(key, raising=False)
    get_settings.cache_clear()


def test_defaults() -> None:
    s = Settings()
    assert s.profile == "local"
    assert s.log_level == "INFO"
    assert s.log_format == "console"
    assert s.trace_dir == Path("./.range/trace")
    assert s.anthropic_api_key is None


def test_precedence_defaults_lt_file_lt_env(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    cfg = tmp_path / "range.env"
    cfg.write_text("RANGE_LOG_LEVEL=DEBUG\n")
    monkeypatch.setenv("RANGE_CONFIG", str(cfg))

    get_settings.cache_clear()
    assert get_settings().log_level == "DEBUG"  # file overrides the default

    monkeypatch.setenv("RANGE_LOG_LEVEL", "ERROR")
    get_settings.cache_clear()
    assert get_settings().log_level == "ERROR"  # env overrides the file


def test_get_settings_is_cached() -> None:
    assert get_settings() is get_settings()


def test_prod_profile_flips_log_format_to_json() -> None:
    assert Settings(profile="prod").log_format == "json"


def test_explicit_log_format_survives_prod() -> None:
    assert Settings(profile="prod", log_format="console").log_format == "console"


def test_secret_str_is_masked() -> None:
    s = Settings(anthropic_api_key="sk-super-secret")  # type: ignore[arg-type]
    assert "sk-super-secret" not in repr(s)
    assert str(s.anthropic_api_key) == "**********"
    assert s.anthropic_api_key is not None
    assert s.anthropic_api_key.get_secret_value() == "sk-super-secret"
