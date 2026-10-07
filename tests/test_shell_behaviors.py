from __future__ import annotations

import os
import shutil
import subprocess
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from pathlib import Path

from tests.test_shell_integration import (
    GIT_BASH_EXECUTABLE,
    _create_uv_environment,
    _documented_loader,
    _environment_with_current_scripts_on_path,
    _write_fake_uvg,
)
from uvg.core.shell import (
    IS_WINDOWS,
    ShellName,
    get_activation_script_path,
    render_activation_command,
    render_path_for_shell,
    render_shell_hook,
)

SHELLS = [ShellName.bash, ShellName.pwsh] if IS_WINDOWS else [ShellName.bash, ShellName.zsh]


def _run(
    tmp_path: Path,
    shell: ShellName,
    script: str,
    environment: dict[str, str],
) -> subprocess.CompletedProcess[str]:
    path = tmp_path / ("check.ps1" if shell == ShellName.pwsh else f"check.{shell}")
    path.write_text(script, encoding="utf-8", newline="\n")
    executable = GIT_BASH_EXECUTABLE if IS_WINDOWS and shell.is_posix else shutil.which(shell.value)
    if executable is None:
        pytest.skip(f"{shell} is unavailable")
    arguments = {
        ShellName.bash: ["--noprofile", "--norc"],
        ShellName.zsh: ["-f"],
        ShellName.pwsh: ["-NoProfile", "-NoLogo", "-NonInteractive", "-File"],
    }[shell]
    return subprocess.run(  # noqa: S603
        [executable, *arguments, render_path_for_shell(path, shell)],
        env=environment,
        capture_output=True,
        encoding="utf-8",
        check=False,
    )


@pytest.mark.parametrize("shell", SHELLS)
def test_repeated_activation_switch_and_local_exit(tmp_path: Path, shell: ShellName) -> None:
    home, first = _create_uv_environment(tmp_path)
    second = first.with_name("second")
    uv = shutil.which("uv")
    assert uv is not None
    subprocess.run([uv, "venv", "--quiet", str(second)], check=True)  # noqa: S603
    environment = _environment_with_current_scripts_on_path()
    environment["UVG_HOME"] = str(home)
    if shell.is_posix:
        script = "\n".join(
            [
                "set -e",
                _documented_loader(shell),
                'baseline="$PATH"',
                "uvg activate tools",
                "uvg activate tools",
                "python -c 'import sys; print(\"FIRST=\" + sys.prefix)'",
                "uvg activate second",
                "python -c 'import sys; print(\"SECOND=\" + sys.prefix)'",
                "PATH=''",
                "uvg deactivate",
                '[ "$PATH" = "$baseline" ]',
                '[ -z "${VIRTUAL_ENV-}" ]',
                "printf 'RESTORED\\n'",
            ]
        )
    else:
        script = "\n".join(
            [
                _documented_loader(shell),
                "$baseline = $env:PATH",
                "uvg activate tools",
                "if ($LASTEXITCODE -ne 0) { exit 11 }",
                "uvg activate tools",
                "if ($LASTEXITCODE -ne 0) { exit 12 }",
                "python -c 'import sys; print(\"FIRST=\" + sys.prefix)'",
                "uvg activate second",
                "if ($LASTEXITCODE -ne 0) { exit 13 }",
                "python -c 'import sys; print(\"SECOND=\" + sys.prefix)'",
                "$env:PATH = ''",
                "uvg deactivate",
                "if ($LASTEXITCODE -ne 0) { exit 14 }",
                "if ($env:PATH -ne $baseline -or $env:VIRTUAL_ENV) { exit 15 }",
                "'RESTORED'",
            ]
        )
    result = _run(tmp_path, shell, script, environment)
    assert result.returncode == 0, result.stderr
    lines = result.stdout.splitlines()
    assert f"FIRST={first}" in lines
    assert f"SECOND={second}" in lines
    assert lines[-1] == "RESTORED"


@pytest.mark.parametrize("shell", SHELLS)
def test_inherited_environment_matches_direct_standard_script(
    tmp_path: Path,
    shell: ShellName,
) -> None:
    home, path = _create_uv_environment(tmp_path)
    environment = _environment_with_current_scripts_on_path()
    environment["UVG_HOME"] = str(home)
    environment["VIRTUAL_ENV"] = str(path)
    environment["PATH"] = (
        str(path / ("Scripts" if IS_WINDOWS else "bin")) + os.pathsep + environment["PATH"]
    )
    direct = render_activation_command(get_activation_script_path(path, shell), shell)
    if shell.is_posix:
        before = "set -e\nif typeset -f deactivate >/dev/null 2>&1; then exit 21; fi\n"
        inspect = "\n".join(
            [
                "typeset -f deactivate >/dev/null",
                'printf "ACTIVE=%s\\n" "$VIRTUAL_ENV"',
                'printf "PYTHON=%s\\n" "$(command -v python)"',
            ]
        )
        after = 'printf "PATH=%s\\n" "$PATH"\nprintf "INACTIVE=%s\\n" "${VIRTUAL_ENV-}"'
    else:
        before = "if (Test-Path Function:\\deactivate) { exit 21 }\n"
        inspect = "\n".join(
            [
                "if (-not (Test-Path Function:\\deactivate)) { exit 22 }",
                "'ACTIVE=' + $env:VIRTUAL_ENV",
                "'PYTHON=' + (Get-Command python -CommandType Application).Source",
            ]
        )
        after = "'PATH=' + $env:PATH\n'INACTIVE=' + $env:VIRTUAL_ENV"
    expected = _run(
        tmp_path, shell, before + "\n".join([direct, inspect, "deactivate", after]), environment
    )
    actual = _run(
        tmp_path,
        shell,
        before
        + "\n".join(
            [
                _documented_loader(shell),
                "uvg activate tools",
                inspect,
                "uvg deactivate",
                after,
            ]
        ),
        environment,
    )
    assert expected.returncode == actual.returncode == 0, (expected.stderr, actual.stderr)
    assert actual.stdout == expected.stdout


@pytest.mark.parametrize("shell", SHELLS)
def test_failed_generation_is_not_evaluated(tmp_path: Path, shell: ShellName) -> None:
    bin_directory = tmp_path / "bin"
    bin_directory.mkdir()
    _write_fake_uvg(
        bin_directory,
        "printf '%s\\n' 'UVG_PARTIAL=executed'\nexit 7\n",
        windows_body="@echo off\r\necho $global:UVG_PARTIAL = 'executed'\r\nexit /b 7\r\n",
    )
    if IS_WINDOWS and shell.is_posix:
        (bin_directory / "uvg").write_text(
            "#!/bin/sh\nprintf '%s\\n' 'UVG_PARTIAL=executed'\nexit 7\n",
            encoding="utf-8",
            newline="\n",
        )
    environment = os.environ.copy()
    environment["PATH"] = str(bin_directory) + os.pathsep + environment["PATH"]
    if shell.is_posix:
        check = 'uvg activate tools\n[ "$?" -eq 7 ] || exit 31\n[ -z "${UVG_PARTIAL-}" ]'
    else:
        check = "uvg activate tools\nif ($LASTEXITCODE -ne 7 -or $global:UVG_PARTIAL) { exit 31 }"
    result = _run(tmp_path, shell, render_shell_hook(shell) + "\n" + check, environment)
    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize("shell", SHELLS)
def test_standard_script_failure_is_reported(tmp_path: Path, shell: ShellName) -> None:
    home = tmp_path / "home"
    path = home / "venvs" / "broken"
    script = get_activation_script_path(path, shell)
    script.parent.mkdir(parents=True)
    script.write_text(
        "return 9\n" if shell.is_posix else "throw 'activation failed'\n", encoding="utf-8"
    )
    environment = _environment_with_current_scripts_on_path()
    environment["UVG_HOME"] = str(home)
    if shell.is_posix:
        check = 'uvg activate broken\n[ "$?" -eq 9 ]'
    else:
        check = "uvg activate broken\nif ($LASTEXITCODE -ne 1) { exit 41 }"
    result = _run(tmp_path, shell, _documented_loader(shell) + "\n" + check, environment)
    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize("shell", SHELLS)
def test_missing_deactivate_function_fails_without_executable(
    tmp_path: Path, shell: ShellName
) -> None:
    environment = os.environ.copy()
    if shell.is_posix:
        check = 'PATH=""\nuvg deactivate\n[ "$?" -ne 0 ]'
    else:
        check = "$env:PATH = ''\nuvg deactivate\nif ($LASTEXITCODE -ne 1) { exit 51 }"
    result = _run(tmp_path, shell, render_shell_hook(shell) + "\n" + check, environment)
    assert result.returncode == 0
    assert "no active environment" in result.stderr
