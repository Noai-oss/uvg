"""List managed virtual environments."""

from __future__ import annotations

import typer

from uvg.core.environment import get_venvs_dir, list_environments, read_python_version

app = typer.Typer()


@app.command("list")
def list_environments_command() -> None:
    """List all managed environments."""
    environments, errors = list_environments(get_venvs_dir())
    name_width = max((len(path.name) for path in environments), default=0)
    for path in environments:
        python_version = read_python_version(path) or "unknown"
        typer.echo(f"{path.name:<{name_width}}  {python_version}")
    for error in errors:
        typer.echo(f"Error: {error}", err=True)
    if errors:
        raise typer.Exit(code=1)
