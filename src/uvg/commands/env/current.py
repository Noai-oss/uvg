"""Show the currently active managed environment."""

from __future__ import annotations

import os

import typer

from uvg.core.environment import get_current_name, get_venvs_dir

app = typer.Typer()


@app.command("current")
def show_current_environment_command() -> None:
    """Show the currently active environment."""
    active_environment_name = get_current_name(get_venvs_dir(), os.environ.get("VIRTUAL_ENV"))
    typer.echo(active_environment_name)
