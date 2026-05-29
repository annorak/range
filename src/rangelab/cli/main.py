"""The `range` command. Subcommands are added by later steps."""

import importlib.metadata

import typer

app = typer.Typer(no_args_is_help=True, add_completion=False)


def _version_cb(value: bool) -> None:
    if value:
        typer.echo(importlib.metadata.version("range-lab"))
        raise typer.Exit()


@app.callback()
def main(
    version: bool = typer.Option(
        False,
        "--version",
        callback=_version_cb,
        is_eager=True,
        help="Show the Range version and exit.",
    ),
) -> None:
    """Range — declarative, ephemeral cyber ranges."""
