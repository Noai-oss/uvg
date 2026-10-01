"""Public activation entry point."""

from __future__ import annotations

from typing import Annotated

import typer

from uvg.core.errors import UvgError

app = typer.Typer()


@app.command("activate")
def activate_environment_command(
    environment_name: Annotated[str, typer.Argument(help="Environment name")],
) -> None:
    """Activate an environment in the current shell."""
    del environment_name
    raise UvgError(
        "`uvg activate` cannot modify its parent shell directly.\n\n"
        "Set up shell integration first:\n"
        "  uvg setup <bash|zsh|pwsh> --profile PATH",
    )
