from __future__ import annotations

import typer

from uvg.core.environment import get_current_name


app = typer.Typer()


@app.command("current")
def show_current_environment_command() -> None:
    """Show the currently active environment."""
    active_environment_name = get_current_name()
    typer.echo(active_environment_name)
