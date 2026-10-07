"""Remove managed virtual environments."""

from __future__ import annotations

import os
from typing import Annotated

import typer

from uvg.core.environment import get_venvs_dir, remove, resolve_path

app = typer.Typer()


@app.command("remove")
def remove_environment_command(
    environment_name: Annotated[str, typer.Argument(help="Environment name")],
    *,
    assume_yes: Annotated[
        bool,
        typer.Option("--yes", "-y", help="Remove without confirmation"),
    ] = False,
) -> None:
    """Remove a managed environment."""
    environment_path = resolve_path(get_venvs_dir(), environment_name)
    if not assume_yes:
        should_remove_environment = typer.confirm(
            f"Remove environment '{environment_path.name}' at '{environment_path}'?",
            default=False,
        )
        if not should_remove_environment:
            typer.echo("Aborted.")
            raise typer.Exit(code=0)

    remove(environment_path, os.environ.get("VIRTUAL_ENV"))
    typer.echo(f"Removed environment '{environment_path.name}'")
