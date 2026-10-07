import pytest
from typer.testing import CliRunner

from uvg.__main__ import main
from uvg.cli import app

runner = CliRunner()


def test_version_option() -> None:
    result = runner.invoke(app, ["--version"])

    assert result.exit_code == 0
    assert "uvg v" in result.output


def test_main_returns_usage_exit_code_for_cli_errors(
    capsys: pytest.CaptureFixture[str],
) -> None:
    exit_code = main(["does-not-exist"])

    assert exit_code == 2
    assert "No such command 'does-not-exist'" in capsys.readouterr().err


@pytest.mark.parametrize("command", ["init", "setup"])
def test_obsolete_initialization_commands_are_removed(command: str) -> None:
    result = runner.invoke(app, [command, "bash"])

    assert result.exit_code == 2
    assert f"No such command '{command}'" in result.output


def test_read_only_commands_do_not_require_uv_on_path(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PATH", "")

    result = runner.invoke(app, ["env", "list"])

    assert result.exit_code == 0


def test_direct_activate_reports_error_on_stderr(
    capsys: pytest.CaptureFixture[str],
) -> None:
    exit_code = main(["activate", "tools"])
    captured = capsys.readouterr()

    assert exit_code == 1
    assert captured.out == ""
    assert "cannot modify its parent shell directly" in captured.err
    assert "source " not in captured.err


def test_direct_deactivate_reports_error_on_stderr(
    capsys: pytest.CaptureFixture[str],
) -> None:
    exit_code = main(["deactivate"])
    captured = capsys.readouterr()

    assert exit_code == 1
    assert captured.out == ""
    assert "requires shell integration" in captured.err
