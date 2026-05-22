from __future__ import annotations

import typer

from uvg.core.environment import VENVS_DIR


app = typer.Typer()


@app.command("dir")
def show_environment_dir_command() -> None:
    """Show environment dir."""
    typer.echo(VENVS_DIR)
