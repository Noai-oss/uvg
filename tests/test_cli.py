import pytest
from unittest.mock import patch
from typer.testing import CliRunner


from uvg.cli import app
from uvg.core.errors import UvgError

runner = CliRunner()


def test_version_option():
    result = runner.invoke(app, ["--version"])

    assert result.exit_code == 0
    assert "uvg v" in result.output


@patch("uvg.cli.shutil.which")
def test_command_should_fail_with_value_error(mock_which):
    mock_which.return_value = None
    with pytest.raises(UvgError) as exc_info:
        runner.invoke(app, ["env", "list"], catch_exceptions=False)

    assert "Error: Not found 'uv', please install it first." in str(exc_info.value)
