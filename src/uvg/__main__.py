from __future__ import annotations

import sys
from collections.abc import Sequence

import typer

from uvg.cli import app
from uvg.core.errors import UvgError


def _show_cli_exception(exc: Exception) -> int | None:
    # Avoid importing Typer's private vendored Click exception classes.
    show = getattr(exc, "show", None)
    exit_code = getattr(exc, "exit_code", None)

    if (
        callable(show)
        and isinstance(exit_code, int)
        and not isinstance(exit_code, bool)
    ):
        try:
            show(file=sys.stderr)
            return exit_code
        except Exception:
            return None

    return None


def main(argv: Sequence[str] | None = None) -> int:
    """Main entry point for the uvg CLI."""
    try:
        app(prog_name="uvg", args=argv, standalone_mode=False)
        return 0
    except typer.Exit as exc:
        return exc.exit_code
    except (KeyboardInterrupt, typer.Abort):
        typer.echo("Interrupted.", err=True)
        return 130
    except UvgError as exc:
        typer.echo(f"Error: {exc}", err=True)
        return 1
    except Exception as exc:
        exit_code = _show_cli_exception(exc)
        if exit_code is not None:
            return exit_code
        raise


if __name__ == "__main__":
    sys.exit(main())
