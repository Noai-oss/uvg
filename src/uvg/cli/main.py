from __future__ import annotations

import typer

from .create import create_environment_command
from .activate import activate_environment_command
from .env import (
    list_environments_command,
    show_current_environment_command,
    show_environment_dir_command,
)
from .remove import remove_environment_command
from .init import initialize_shell_integration_command

app = typer.Typer(
    name="uvg",
    help="uvg: a global virtual environment manager built on top of uv",
    add_completion=False,
    no_args_is_help=True,
)

app.command("create")(create_environment_command)
app.command("remove")(remove_environment_command)
app.command("init")(initialize_shell_integration_command)
app.command("activate")(activate_environment_command)


env_app = typer.Typer(
    name="env",
    help="Commands for managing virtual environments",
    add_completion=False,
    no_args_is_help=True,
)

env_app.command("list")(list_environments_command)
env_app.command("dir")(show_environment_dir_command)
env_app.command("current")(show_current_environment_command)

app.add_typer(env_app, name="env", help="Commands for managing virtual environments")
