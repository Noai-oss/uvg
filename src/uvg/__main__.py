from __future__ import annotations

import sys
from collections.abc import Sequence

import click
import typer

from uvg.cli import app
from uvg.core.errors import UvgError


def main(argv: Sequence[str] | None = None) -> int:
    """Main entry point for the uvg CLI."""
    try:
        app(prog_name="uvg", args=argv, standalone_mode=False)
        return 0
    except typer.Exit as exc:
        return exc.exit_code
    except click.ClickException as exc:
        exc.show(file=sys.stderr)
        return exc.exit_code
    except (KeyboardInterrupt, typer.Abort):
        typer.echo("Interrupted.", err=True)
        return 130
    except UvgError as exc:
        typer.echo(f"Error: {exc}", err=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
