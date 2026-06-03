"""Generate shell activation commands for managed environments."""

from __future__ import annotations

import sys
from typing import Annotated

import typer

from uvg.core.environment import resolve_path
from uvg.core.shell import (
    ShellName,
    get_default_shell_type_for_current_platform,
    render_activation_command,
)

app = typer.Typer()


@app.command("activate")
def activate_environment_command(
    environment_name: Annotated[str, typer.Argument(help="Environment name")],
    shell_name: Annotated[
        ShellName | None,
        typer.Option(
            "--shell",
            help="Shell to generate activation code for",
        ),
    ] = None,
) -> None:
    """Generate activation command for an environment."""
    managed_environment_path = resolve_path(environment_name)
    resolved_shell_name = shell_name or get_default_shell_type_for_current_platform()
    activation_command = render_activation_command(
        managed_environment_path,
        resolved_shell_name,
    )
    # Activation output is shell code consumed by eval/Invoke-Expression.
    sys.stdout.buffer.write(f"{activation_command}\n".encode())
