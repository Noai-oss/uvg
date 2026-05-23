from __future__ import annotations

import shutil

import typer

from uvg import __version__
from uvg.commands import activate, create, init, remove
from uvg.commands.env import app as env_app
from uvg.core.errors import UvgError

app = typer.Typer(
    name="uvg",
    help="uvg: a global virtual environment manager built on top of uv",
    add_completion=False,
    no_args_is_help=True,
)


def version_callback(value: bool):
    if value:
        typer.echo(f"uvg v{__version__}")
        raise typer.Exit()


@app.callback()
def callback_func(
    version: bool = typer.Option(
        None,
        "--version",
        "-v",
        help="Show version and exit",
        callback=version_callback,
        is_eager=True,
    ),
):
    if shutil.which("uv") is None:
        raise UvgError("Error: Not found 'uv', please install it first.")


app.add_typer(create.app)
app.add_typer(remove.app)
app.add_typer(init.app)
app.add_typer(activate.app)
app.add_typer(env_app, name="env", help="Commands for managing virtual environments")
