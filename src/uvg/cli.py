"""Typer application wiring for the uvg CLI."""

from __future__ import annotations

import typer

from uvg import __version__
from uvg.commands import activate, create, deactivate, remove, setup, shell
from uvg.commands.env import app as env_app

app = typer.Typer(
    name="uvg",
    help="uvg: a global virtual environment manager built on top of uv",
    add_completion=False,
    no_args_is_help=True,
    context_settings={"help_option_names": ["-h", "--help"]},
)


def version_callback(value: bool) -> None:  # noqa: FBT001
    """Print the version and exit when the version option is set."""
    if value:
        typer.echo(f"uvg v{__version__}")
        raise typer.Exit


@app.callback()
def callback_func(
    _version: bool = typer.Option(  # noqa: FBT001
        None,
        "--version",
        "-v",
        help="Show version and exit",
        callback=version_callback,
        is_eager=True,
    ),
) -> None:
    """Handle application-wide options."""


app.add_typer(create.app)
app.add_typer(remove.app)
app.add_typer(setup.app)
app.add_typer(activate.app)
app.add_typer(deactivate.app)
app.add_typer(env_app, name="env", help="Commands for managing virtual environments")
app.add_typer(shell.app, name="shell", help="Generate shell integration code")
