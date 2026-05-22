from __future__ import annotations

import typer

from uvg.core.environment import get_venvs_dir


app = typer.Typer()


@app.command("dir")
def show_environment_dir_command() -> None:
    """Show environment dir."""
    typer.echo(get_venvs_dir())
