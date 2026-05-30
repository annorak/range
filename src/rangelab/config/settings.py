"""Process settings: 12-factor load (defaults → RANGE_CONFIG file → RANGE_* env)."""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Range configuration. Secrets are `SecretStr` so they never render in logs."""

    model_config = SettingsConfigDict(
        env_prefix="RANGE_",
        env_file=os.getenv("RANGE_CONFIG"),
        extra="ignore",
    )

    profile: Literal["local", "ci", "prod"] = "local"
    log_level: str = "INFO"
    log_format: Literal["console", "json"] = "console"
    anthropic_api_key: SecretStr | None = None
    openai_api_key: SecretStr | None = None
    postgres_url: str | None = None
    trace_dir: Path = Path("./.range/trace")

    @model_validator(mode="after")
    def _json_logs_in_prod(self) -> Settings:
        """Prod defaults to JSON logs unless the format was set explicitly."""
        if self.profile == "prod" and "log_format" not in self.model_fields_set:
            object.__setattr__(self, "log_format", "json")
        return self


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Process-wide settings singleton. `RANGE_CONFIG` is resolved at call time."""
    # `_env_file` is pydantic-settings' per-call dotenv override; it isn't part of
    # the field-derived __init__ mypy sees, so the call-arg ignore is expected.
    return Settings(_env_file=os.getenv("RANGE_CONFIG"))  # type: ignore[call-arg]
