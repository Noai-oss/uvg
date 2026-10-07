"""Low-level shell code generation commands."""

from __future__ import annotations

import stat
import sys
from typing import Annotated

import typer

from uvg.core.environment import get_venvs_dir, resolve_path
from uvg.core.errors import UvgError
from uvg.core.shell import (
    ShellName,
    get_activation_script_path,
    render_activation_command,
    render_shell_hook,
)

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
    environment_path = resolve_path(get_venvs_dir(), environment_name)
    script_path = get_activation_script_path(environment_path, shell_name)
    try:
        mode = script_path.stat().st_mode
    except FileNotFoundError as exc:
        raise UvgError(f"Missing activation script:\n  {script_path}") from exc
    except OSError as exc:
        raise UvgError(f"Could not read activation script '{script_path}': {exc}") from exc
    if not stat.S_ISREG(mode):
        raise UvgError(f"Activation script is not a regular file: {script_path}")
    _write_shell_code(render_activation_command(script_path, shell_name))


def _write_shell_code(code: str) -> None:
    """Write shell code as UTF-8 with a platform-independent newline."""
    sys.stdout.buffer.write(f"{code}\n".encode())
