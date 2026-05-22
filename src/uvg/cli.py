from __future__ import annotations

import typer

from uvg.commands import activate, create, init, remove
from uvg.commands.env import app as env_app


app = typer.Typer(
    name="uvg",
    help="uvg: a global virtual environment manager built on top of uv",
    add_completion=False,
    no_args_is_help=True,
)

app.add_typer(create.app)
app.add_typer(remove.app)
app.add_typer(init.app)
app.add_typer(activate.app)
app.add_typer(env_app, name="env", help="Commands for managing virtual environments")
