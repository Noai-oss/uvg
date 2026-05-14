from __future__ import annotations

import typer

from uvg.core.environment import (
    VENVS_DIR,
    build_path,
    get_current_name,
    list_names,
    read_python_version,
)


def list_environments_command() -> None:
    """List all managed environments."""
    environment_names = list_names()
    if not environment_names:
        return

    name_width = max(len(environment_name) for environment_name in environment_names)
    for environment_name in environment_names:
        environment_path = build_path(environment_name)
        python_version = read_python_version(environment_path) or "unknown"
        typer.echo(f"{environment_name:<{name_width}}  {python_version}")


def show_current_environment_command() -> None:
    """Show the currently active environment."""
    active_environment_name = get_current_name()
    typer.echo(active_environment_name)


def show_environment_dir_command() -> None:
    """Show environment dir."""
    typer.echo(VENVS_DIR)
