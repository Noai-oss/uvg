from __future__ import annotations

from typing import Annotated

import typer

from uvg.core.environment import remove


app = typer.Typer()


@app.command("remove")
def remove_environment_command(
    environment_name: Annotated[str, typer.Argument(help="Environment name")],
    assume_yes: Annotated[
        bool,
        typer.Option("--yes", "-y", help="Remove without confirmation"),
    ] = False,
) -> None:
    """Remove a managed environment."""
    if not assume_yes:
        should_remove_environment = typer.confirm(
            f"Remove environment '{environment_name}'?",
            default=False,
        )
        if not should_remove_environment:
            typer.echo("Aborted.")
            raise typer.Exit(code=0)

    remove(environment_name)
    typer.echo(f"Removed environment '{environment_name}'")
