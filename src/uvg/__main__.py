"""Command-line entry point for uvg."""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING

import typer
from typer._click.exceptions import ClickException

from uvg.cli import app
from uvg.core.errors import UvgError

if TYPE_CHECKING:
    from collections.abc import Sequence


def main(argv: Sequence[str] | None = None) -> int:
    """Run the uvg CLI."""
    try:
        app(prog_name="uvg", args=argv, standalone_mode=False)
    except typer.Exit as exc:
        return exc.exit_code
    except ClickException as exc:
        exc.show(file=sys.stderr)
        return exc.exit_code
    except (KeyboardInterrupt, typer.Abort):
        typer.echo("Interrupted.", err=True)
        return 130
    except UvgError as exc:
        typer.echo(f"Error: {exc}", err=True)
        return 1
    else:
        return 0


if __name__ == "__main__":
    sys.exit(main())
