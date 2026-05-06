from __future__ import annotations

import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Annotated

import click
import typer

from .environment import (
    create_managed_environment,
    current_environment_name,
    get_managed_environment_info,
    list_managed_environment_names,
    remove_managed_environment,
    resolve_managed_environment_path,
)
from .errors import UvgError
from .shell import (
    ShellType,
    append_shell_integration_to_profile,
    get_default_shell_type_for_current_platform,
    render_activation_command,
    render_shell_integration_script,
)


app = typer.Typer(
    name="uvg",
    help="uvg: a global virtual environment manager built on top of uv",
    add_completion=False,
    no_args_is_help=True,
)


# ============================================================================
# Commands: create
# ============================================================================


@app.command("create")
def create_environment_command(
    environment_name: Annotated[str, typer.Argument(help="Environment name")],
    python_version: Annotated[
        str | None,
        typer.Option("--python", "-p", help="Python version to use, for example 3.12"),
    ] = None,
) -> None:
    """Create a new managed environment."""
    managed_environment_path = create_managed_environment(
        environment_name, python_version
    )
    typer.echo(f"Created environment '{managed_environment_path.name}'")
    typer.echo(f"Path: {managed_environment_path}")


# ============================================================================
# Commands: activate
# ============================================================================


@app.command("activate")
def activate_environment_command(
    environment_name: Annotated[str, typer.Argument(help="Environment name")],
    shell_name: Annotated[
        ShellType | None,
        typer.Option(
            "--shell",
            help="Shell to generate activation code for",
        ),
    ] = None,
) -> None:
    """Generate activation command for an environment."""
    managed_environment_path = resolve_managed_environment_path(environment_name)
    resolved_shell_name = shell_name or get_default_shell_type_for_current_platform()
    typer.echo(render_activation_command(managed_environment_path, resolved_shell_name))


# ============================================================================
# Commands: list
# ============================================================================


@app.command("list")
def list_environments_command() -> None:
    """List all managed environments."""
    for environment_name in list_managed_environment_names():
        typer.echo(environment_name)


# ============================================================================
# Commands: path
# ============================================================================


@app.command("path")
def show_environment_path_command(
    environment_name: Annotated[str, typer.Argument(help="Environment name")],
) -> None:
    """Show the path to an environment."""
    managed_environment_path = resolve_managed_environment_path(environment_name)
    typer.echo(managed_environment_path)


# ============================================================================
# Commands: current
# ============================================================================


@app.command("current")
def show_current_environment_command() -> None:
    """Show the currently active environment."""
    active_environment_name = current_environment_name()
    typer.echo(active_environment_name)


# ============================================================================
# Commands: info
# ============================================================================


@app.command("info")
def show_environment_info_command(
    environment_name: Annotated[str, typer.Argument(help="Environment name")],
) -> None:
    """Show detailed information about an environment."""
    environment_info = get_managed_environment_info(environment_name)
    typer.echo(f"Name: {environment_info.name}")
    typer.echo(f"Path: {environment_info.path}")
    typer.echo(f"Python: {environment_info.python_executable}")


# ============================================================================
# Commands: remove
# ============================================================================


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
            raise typer.Exit(code=1)

    remove_managed_environment(environment_name)
    typer.echo(f"Removed environment '{environment_name}'")


# ============================================================================
# Commands: init
# ============================================================================


@app.command("init")
def initialize_shell_integration_command(
    shell_name: Annotated[ShellType, typer.Argument(help="Shell type")],
    profile_path: Annotated[
        Path | None,
        typer.Option(
            "--profile",
            "-p",
            help="Append the shell integration snippet to the given profile file",
        ),
    ] = None,
) -> None:
    """Initialize shell integration for uvg."""
    if profile_path is None:
        typer.echo(render_shell_integration_script(shell_name))
        return

    expanded_profile_path = profile_path.expanduser()
    did_append_profile_snippet = append_shell_integration_to_profile(
        shell_name,
        expanded_profile_path,
    )

    if not did_append_profile_snippet:
        typer.echo(f"uvg initialization is already present in {expanded_profile_path}")
        return

    typer.echo(f"Successfully appended uvg initialization to {expanded_profile_path}")
    typer.echo("Please restart your shell or source your profile to apply changes.")


# ============================================================================
# Main Entry Point
# ============================================================================


def main(argv: Sequence[str] | None = None) -> int:
    """Main entry point for the uvg CLI."""
    try:
        app(prog_name="uvg", args=argv, standalone_mode=False)
        return 0
    except typer.Exit as exc:
        return exc.exit_code
    except click.ClickException as exc:
        exc.show(file=sys.stderr)
        return exc.exit_code
    except (KeyboardInterrupt, typer.Abort):
        typer.echo("Interrupted.", err=True)
        return 130
    except UvgError as exc:
        typer.echo(f"Error: {exc}", err=True)
        return 1
