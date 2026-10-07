"""Public deactivation entry point."""

from __future__ import annotations

import typer

from uvg.core.errors import UvgError

app = typer.Typer()


@app.command("deactivate")
def deactivate_environment_command() -> None:
    """Deactivate the current environment."""
    raise UvgError(
        "`uvg deactivate` requires shell integration.\n"
        "Add the documented `uvg shell hook <bash|zsh|pwsh>` loader to your profile,\n"
        "then restart your shell. See the README Shell integration section.",
    )
