"""Smoke test for the `range` CLI entrypoint (Step 0.1's only feature surface)."""

from typer.testing import CliRunner

from rangelab import __version__
from rangelab.cli.main import _version_cb, app

runner = CliRunner()


def test_version_flag_prints_version() -> None:
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert result.stdout.strip() == __version__


def test_version_callback_is_noop_when_unset() -> None:
    # The eager callback fires with a falsy value when --version is absent; it must
    # do nothing (no echo, no Exit) so normal subcommands run.
    assert _version_cb(False) is None
