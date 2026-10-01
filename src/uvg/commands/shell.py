"""Low-level shell code generation commands."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Annotated

import typer

from uvg.core.environment import resolve_path
from uvg.core.shell import ShellName, render_activation_command, render_shell_hook

app = typer.Typer(
    name="shell",
    help="Generate shell integration code",
    add_completion=False,
    no_args_is_help=True,
)


@app.command("hook")
def shell_hook_command(
    shell_name: Annotated[ShellName, typer.Argument(help="Shell syntax to generate")],
) -> None:
    """Generate the complete runtime hook for a shell."""
    _write_shell_code(render_shell_hook(shell_name))


@app.command("activate")
def shell_activate_command(
    shell_name: Annotated[ShellName, typer.Argument(help="Shell syntax to generate")],
    environment_name: Annotated[str, typer.Argument(help="Environment name")],
) -> None:
    """Generate code that activates a managed environment."""
    environment_path = resolve_path(environment_name)
    active_environment = os.environ.get("VIRTUAL_ENV")
    if active_environment and _paths_are_equal(Path(active_environment), environment_path):
        _write_shell_code(":" if shell_name.is_posix else "$null = $null")
        return

    _write_shell_code(render_activation_command(environment_path, shell_name))


def _write_shell_code(code: str) -> None:
    """Write shell code as UTF-8 with a platform-independent newline."""
    sys.stdout.buffer.write(f"{code}\n".encode())


def _paths_are_equal(first: Path, second: Path) -> bool:
    try:
        return first.resolve() == second.resolve()
    except OSError:
        return False
