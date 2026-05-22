from __future__ import annotations

import sys
from pathlib import Path
from typing import Annotated

import typer

from uvg.core.shell import (
    IS_WINDOWS,
    ShellName,
    append_shell_integration_to_profile,
    convert_windows_path_to_msys_path,
    render_shell_integration_script,
)


app = typer.Typer()


@app.command("init")
def initialize_shell_integration_command(
    shell_name: Annotated[ShellName, typer.Argument(help="Shell type")],
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
        script_content = render_shell_integration_script(shell_name) + "\n"
        # Shell integration output is shell code consumed by eval/Invoke-Expression.
        sys.stdout.buffer.write(script_content.encode("utf-8"))
        return

    expanded_profile_path = profile_path.expanduser()
    did_append_profile_snippet = append_shell_integration_to_profile(
        shell_name,
        expanded_profile_path,
    )

    if not did_append_profile_snippet:
        typer.echo(f"uvg initialization is already present in {expanded_profile_path}")
        return

    expanded_profile_path_str = (
        convert_windows_path_to_msys_path(expanded_profile_path)
        if IS_WINDOWS
        else str(expanded_profile_path)
    )
    typer.echo(
        f"Successfully appended uvg initialization to {expanded_profile_path_str}"
    )
    typer.echo("Please restart your shell or source your profile to apply changes.")
