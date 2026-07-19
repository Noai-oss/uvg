"""Install and remove shell profile integration."""

from __future__ import annotations

import shlex
from pathlib import Path  # noqa: TC003
from typing import Annotated

import typer

from uvg.core.profile import (
    ProfileAction,
    ProfileChange,
    apply_profile_change,
    plan_profile_change,
)
from uvg.core.shell import (
    ShellName,
    quote_pwsh_string_literal,
    render_path_for_shell,
)

app = typer.Typer()


@app.command("setup")
def setup_shell_integration_command(
    shell_name: Annotated[ShellName, typer.Argument(help="Shell syntax to install")],
    profile_path: Annotated[
        Path,
        typer.Option(
            "--profile",
            "-p",
            help="Profile file to modify (required)",
            dir_okay=False,
        ),
    ],
    *,
    dry_run: Annotated[
        bool,
        typer.Option("--dry-run", help="Print the planned change without writing"),
    ] = False,
    remove: Annotated[
        bool,
        typer.Option("--remove", help="Remove uvg integration from the profile"),
    ] = False,
) -> None:
    """Set up shell integration in an explicitly selected profile."""
    change = plan_profile_change(shell_name, profile_path, remove=remove)
    if dry_run:
        _print_dry_run(shell_name, change)
        return

    apply_profile_change(change)
    _print_result(shell_name, change, remove=remove)


def _print_dry_run(
    shell_name: ShellName,
    change: ProfileChange,
) -> None:
    typer.echo(f"Plan: {change.action.value} uvg for {shell_name.value}")
    typer.echo(f"Profile: {change.path}")
    if change.line_endings_normalized:
        typer.echo(f"Line endings: normalize to {_newline_name(change.newline)}")
    diff = change.render_diff()
    if diff:
        typer.echo()
        typer.echo(diff, nl=False)


def _print_result(
    shell_name: ShellName,
    change: ProfileChange,
    *,
    remove: bool,
) -> None:
    action = change.action
    if action is ProfileAction.no_change:
        message = (
            f"uvg integration was not found for {shell_name.value}"
            if remove
            else f"uvg is already configured for {shell_name.value}"
        )
        typer.echo(message)
        typer.echo(f"Profile: {change.path}")
        return

    verb = {
        ProfileAction.initialize: "Initialized",
        ProfileAction.update: "Updated",
        ProfileAction.remove: "Removed",
    }[action]
    typer.echo(f"{verb} uvg for {shell_name.value}")
    typer.echo(f"Profile: {change.path}")
    if change.line_endings_normalized:
        typer.echo(f"Normalized line endings: {_newline_name(change.newline)}")
    typer.echo()
    if action is ProfileAction.remove:
        typer.echo(f"Restart {shell_name.value} to discard the integration from this session.")
        return

    typer.echo(f"Restart {shell_name.value} or reload the profile:")
    typer.echo(f"  {_render_reload_command(shell_name, change.path)}")


def _newline_name(newline: str) -> str:
    return "CRLF" if newline == "\r\n" else "LF"


def _render_reload_command(shell_name: ShellName, profile_path: Path) -> str:
    rendered_path = render_path_for_shell(profile_path, shell_name)
    if shell_name.is_posix:
        return f"source {shlex.quote(rendered_path)}"
    return f". {quote_pwsh_string_literal(rendered_path)}"
