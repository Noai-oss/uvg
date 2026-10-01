"""Create managed virtual environments."""

from __future__ import annotations

from typing import Annotated

import typer

from uvg.core.environment import create, read_python_version

app = typer.Typer()


@app.command("create")
def create_environment_command(
    environment_name: Annotated[str, typer.Argument(help="Environment name")],
    python_version: Annotated[
        str | None,
        typer.Option("--python", "-p", help="Python version to use, for example 3.12"),
    ] = None,
) -> None:
    """Create a new managed environment."""
    managed_environment_path = create(environment_name, python_version)
    typer.echo(f"Created environment '{managed_environment_path.name}'")
    typer.echo(f"Python: {read_python_version(managed_environment_path) or 'unknown'}")
    typer.echo(f"Path: {managed_environment_path}")
    typer.echo()
    typer.echo("Activate with:")
    typer.echo(f"  uvg activate {managed_environment_path.name}")
