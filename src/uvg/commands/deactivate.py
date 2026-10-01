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
        "Run `uvg setup <bash|zsh|pwsh> --profile PATH`, then restart your shell.",
    )
