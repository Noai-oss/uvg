from __future__ import annotations

import typer

from uvg.commands.env import current, directory
from uvg.commands.env import list as list_command


app = typer.Typer(
    name="env",
    help="Commands for managing virtual environments",
    add_completion=False,
    no_args_is_help=True,
)

app.add_typer(list_command.app)
app.add_typer(directory.app)
app.add_typer(current.app)
