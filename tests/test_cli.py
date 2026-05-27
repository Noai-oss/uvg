from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from uvg.__main__ import main
from uvg.cli import app
from uvg.core.errors import UvgError

runner = CliRunner()


def test_version_option():
    result = runner.invoke(app, ["--version"])

    assert result.exit_code == 0
    assert "uvg v" in result.output


def test_main_returns_usage_exit_code_for_cli_errors(capsys):
    exit_code = main(["does-not-exist"])

    assert exit_code == 2
    assert "No such command 'does-not-exist'" in capsys.readouterr().err


@patch("uvg.cli.shutil.which")
def test_main_returns_error_when_uv_missing(mock_which, capsys):
    mock_which.side_effect = lambda executable: (
        None if executable == "uv" else executable
    )

    exit_code = main(["env", "list"])

    assert exit_code == 1
    assert "Error: Not found 'uv', please install it first." in capsys.readouterr().err


def test_main_reraises_non_cli_exceptions_with_incompatible_show():
    class NonCliError(Exception):
        exit_code = 2

        def show(self):
            raise AssertionError("This should not replace the original exception.")

    with (
        patch("uvg.__main__.app", side_effect=NonCliError("boom")),
        pytest.raises(NonCliError, match="boom"),
    ):
        main([])


@patch("uvg.cli.shutil.which")
def test_command_should_fail_when_uv_missing(mock_which):
    mock_which.side_effect = lambda executable: (
        None if executable == "uv" else executable
    )

    with pytest.raises(UvgError) as exc_info:
        runner.invoke(app, ["env", "list"], catch_exceptions=False)

    assert "Not found 'uv', please install it first." in str(exc_info.value)
    mock_which.assert_called_once_with("uv")
