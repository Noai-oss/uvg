from __future__ import annotations

import os
import re
import shlex
import shutil
import stat
import subprocess
import sys
from codecs import BOM_UTF8
from pathlib import Path
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from uvg.cli import app
from uvg.core.errors import UvgError
from uvg.core.profile import (
    ProfileAction,
    apply_profile_change,
    plan_profile_change,
    render_profile_block,
    start_marker,
)
from uvg.core.shell import (
    IS_WINDOWS,
    ShellName,
    get_activation_script_path,
    quote_pwsh_string_literal,
    render_activation_command,
    render_path_for_shell,
    render_profile_loader,
    render_shell_hook,
)

runner = CliRunner()
POSIX_SHELL_CASES = [
    (ShellName.bash, "bash", ("--noprofile", "--norc")),
    (ShellName.zsh, "zsh", ("-f",)),
]


def _find_git_bash() -> str | None:
    if os.name != "nt":
        return None

    git_executable = shutil.which("git")
    if git_executable is None:
        return None

    git_path = Path(git_executable).resolve()
    roots = [git_path.parent.parent, git_path.parent.parent.parent]
    for root in roots:
        for relative_path in (Path("bin/bash.exe"), Path("usr/bin/bash.exe")):
            candidate = root / relative_path
            if candidate.is_file():
                return str(candidate)
    return None


GIT_BASH_EXECUTABLE = _find_git_bash()


def _environment_with_current_scripts_on_path() -> dict[str, str]:
    environment = os.environ.copy()
    scripts_directory = str(Path(sys.executable).parent)
    existing_path = environment.get("PATH")
    environment["PATH"] = (
        scripts_directory
        if not existing_path
        else os.pathsep.join([scripts_directory, existing_path])
    )
    return environment


def _create_activation_script(environment_path: Path, shell_name: ShellName) -> Path:
    activation_script_path = get_activation_script_path(environment_path, shell_name)
    activation_script_path.parent.mkdir(parents=True)
    activation_script_path.write_text("# activation\n", encoding="utf-8")
    return activation_script_path


def _write_fake_uvg(
    bin_directory: Path,
    posix_body: str,
    *,
    windows_body: str | None = None,
) -> None:
    if os.name == "nt":
        assert windows_body is not None
        fake_uvg = bin_directory / "uvg.cmd"
        fake_uvg.write_text(windows_body, encoding="utf-8")
        return

    fake_uvg = bin_directory / "uvg"
    fake_uvg.write_text(f"#!/bin/sh\n{posix_body}", encoding="utf-8")
    fake_uvg.chmod(fake_uvg.stat().st_mode | stat.S_IXUSR)


def _create_uv_environment(tmp_path: Path) -> tuple[Path, Path]:
    uv_executable = shutil.which("uv")
    assert uv_executable is not None
    uvg_home = tmp_path / "uvg home"
    environment_path = uvg_home / "venvs" / "tools"
    subprocess.run(  # noqa: S603
        [uv_executable, "venv", "--quiet", str(environment_path)],
        check=True,
    )
    return uvg_home, environment_path


@pytest.mark.parametrize("shell_name", [ShellName.bash, ShellName.zsh])
def test_posix_profile_loader_loads_current_nonempty_hook_at_startup(
    shell_name: ShellName,
) -> None:
    loader = render_profile_loader(shell_name)

    assert f"command uvg shell hook {shell_name.value}" in loader
    assert 'if [ -n "$_uvg_hook" ]' in loader
    assert 'eval "$_uvg_hook"' in loader
    assert "unset _uvg_hook" in loader
    assert "_UVG_SHELL_HOOK" not in loader


def test_pwsh_profile_loader_loads_current_nonempty_hook_at_startup() -> None:
    loader = render_profile_loader(ShellName.pwsh)

    assert "Get-Command uvg -CommandType Application" in loader
    assert "shell hook pwsh" in loader
    assert "[string]::IsNullOrWhiteSpace($uvgHookText)" in loader
    assert "Invoke-Expression $uvgHookText" in loader
    assert "Remove-Variable uvgCommand, uvgHook, uvgHookText" in loader
    assert "_UVG_SHELL_HOOK" not in loader


@pytest.mark.skipif(os.name == "nt", reason="POSIX shell executable test")
@pytest.mark.parametrize(
    ("shell_name", "executable_name", "shell_arguments"),
    POSIX_SHELL_CASES,
)
def test_posix_profile_loader_does_not_eval_partial_output_after_failure(
    tmp_path: Path,
    shell_name: ShellName,
    executable_name: str,
    shell_arguments: tuple[str, ...],
) -> None:
    shell_executable = shutil.which(executable_name)
    if shell_executable is None:
        pytest.skip(f"{executable_name} is unavailable")

    bin_directory = tmp_path / "bin"
    bin_directory.mkdir()
    _write_fake_uvg(
        bin_directory,
        "printf '%s\\n' 'UVG_PARTIAL=executed'\nexit 1\n",
    )
    profile_path = tmp_path / "profile"
    profile_path.write_text(render_profile_block(shell_name), encoding="utf-8")
    environment = os.environ.copy()
    environment["PATH"] = os.pathsep.join([str(bin_directory), environment["PATH"]])

    completed_process = subprocess.run(  # noqa: S603
        [
            shell_executable,
            *shell_arguments,
            "-c",
            (f'source {shlex.quote(str(profile_path))}; printf "%s\\n" "${{UVG_PARTIAL-unset}}"'),
        ],
        check=False,
        capture_output=True,
        env=environment,
        text=True,
    )

    assert completed_process.returncode == 0, completed_process.stderr
    assert completed_process.stdout == "unset\n"


@pytest.mark.skipif(shutil.which("pwsh") is None, reason="PowerShell 7 is unavailable")
def test_pwsh_profile_loader_does_not_invoke_partial_output_after_failure(
    tmp_path: Path,
) -> None:
    pwsh_executable = shutil.which("pwsh")
    assert pwsh_executable is not None
    bin_directory = tmp_path / "bin"
    bin_directory.mkdir()
    _write_fake_uvg(
        bin_directory,
        "printf '%s\\n' \"\\$global:UVG_PARTIAL = 'executed'\"\nexit 1\n",
        windows_body=("@echo off\r\necho $global:UVG_PARTIAL = 'executed'\r\nexit /b 1\r\n"),
    )
    profile_path = tmp_path / "profile.ps1"
    profile_path.write_text(render_profile_block(ShellName.pwsh), encoding="utf-8")
    verification_script = tmp_path / "verify.ps1"
    verification_script.write_text(
        "\n".join(
            [
                f". {quote_pwsh_string_literal(str(profile_path))}",
                'if ($global:UVG_PARTIAL -eq "executed") { exit 9 }',
            ],
        ),
        encoding="utf-8",
    )
    environment = os.environ.copy()
    environment["PATH"] = os.pathsep.join([str(bin_directory), environment["PATH"]])

    completed_process = subprocess.run(  # noqa: S603
        [
            pwsh_executable,
            "-NoLogo",
            "-NoProfile",
            "-NonInteractive",
            "-File",
            str(verification_script),
        ],
        check=False,
        capture_output=True,
        env=environment,
        text=True,
    )

    assert completed_process.returncode == 0, completed_process.stderr


@pytest.mark.parametrize("shell_name", list(ShellName))
def test_shell_hook_does_not_set_uv_project_environment(shell_name: ShellName) -> None:
    assert "UV_PROJECT_ENVIRONMENT" not in render_shell_hook(shell_name)


@pytest.mark.skipif(os.name == "nt", reason="POSIX shell executable test")
@pytest.mark.parametrize(
    ("shell_name", "executable_name", "shell_arguments"),
    POSIX_SHELL_CASES,
)
def test_posix_hook_routes_commands_and_preserves_status(
    tmp_path: Path,
    shell_name: ShellName,
    executable_name: str,
    shell_arguments: tuple[str, ...],
) -> None:
    shell_executable = shutil.which(executable_name)
    if shell_executable is None:
        pytest.skip(f"{executable_name} is unavailable")

    bin_directory = tmp_path / "bin"
    bin_directory.mkdir()
    _write_fake_uvg(
        bin_directory,
        """if [ "$#" -eq 4 ] && [ "$1" = "shell" ] && [ "$2" = "activate" ]; then
    printf "%s\\n" "UVG_ROUTED='$3:$4'"
    exit 0
fi
printf "CALL"
for argument in "$@"; do
    printf "<%s>" "$argument"
done
printf "\\n"
if [ "$1" = "fail" ]; then
    exit 7
fi
""",
    )
    hook_path = tmp_path / "hook"
    hook_path.write_text(render_shell_hook(shell_name), encoding="utf-8")
    verification_script = tmp_path / "verify"
    verification_script.write_text(
        "\n".join(
            [
                f"source {shlex.quote(str(hook_path))}",
                "uvg activate tools",
                'printf "ROUTED=%s\\n" "$UVG_ROUTED"',
                "uvg activate --help",
                "uvg activate tools extra",
                "uvg deactivate extra",
                'uvg passthrough "two words"',
                "uvg fail",
                'printf "STATUS=%s\\n" "$?"',
            ],
        ),
        encoding="utf-8",
    )
    environment = os.environ.copy()
    environment["PATH"] = os.pathsep.join([str(bin_directory), environment["PATH"]])

    completed_process = subprocess.run(  # noqa: S603
        [shell_executable, *shell_arguments, str(verification_script)],
        check=False,
        capture_output=True,
        env=environment,
        text=True,
    )

    assert completed_process.returncode == 0, completed_process.stderr
    assert completed_process.stdout.splitlines() == [
        f"ROUTED={shell_name.value}:tools",
        "CALL<activate><--help>",
        "CALL<activate><tools><extra>",
        "CALL<deactivate><extra>",
        "CALL<passthrough><two words>",
        "CALL<fail>",
        "STATUS=7",
    ]


@pytest.mark.skipif(shutil.which("pwsh") is None, reason="PowerShell 7 is unavailable")
def test_pwsh_hook_routes_commands_and_preserves_status(
    tmp_path: Path,
) -> None:
    pwsh_executable = shutil.which("pwsh")
    assert pwsh_executable is not None
    bin_directory = tmp_path / "bin"
    bin_directory.mkdir()
    _write_fake_uvg(
        bin_directory,
        """if [ "$#" -eq 4 ] && [ "$1" = "shell" ] && [ "$2" = "activate" ]; then
    printf "%s\\n" "\\$global:UVG_ROUTED = '$3:$4'"
    exit 0
fi
printf "CALL<%s><%s><%s>\\n" "$1" "$2" "$3"
if [ "$1" = "fail" ]; then
    exit 7
fi
""",
        windows_body="""@echo off
if "%~1"=="shell" if "%~2"=="activate" (
    echo $global:UVG_ROUTED = '%~3:%~4'
    exit /b 0
)
echo CALL^<%~1^>^<%~2^>^<%~3^>
if "%~1"=="fail" exit /b 7
""",
    )
    hook_path = tmp_path / "hook.ps1"
    hook_path.write_text(render_shell_hook(ShellName.pwsh), encoding="utf-8")
    verification_script = tmp_path / "verify.ps1"
    verification_script.write_text(
        "\n".join(
            [
                f". {quote_pwsh_string_literal(str(hook_path))}",
                "uvg activate tools",
                '[Console]::Out.WriteLine("ROUTED=" + $global:UVG_ROUTED)',
                "uvg activate --help",
                "uvg activate tools extra",
                "uvg deactivate extra",
                'uvg passthrough "two words"',
                "uvg fail",
                '[Console]::Out.WriteLine("STATUS=" + $global:LASTEXITCODE)',
            ],
        ),
        encoding="utf-8",
    )
    environment = os.environ.copy()
    environment["PATH"] = os.pathsep.join([str(bin_directory), environment["PATH"]])

    completed_process = subprocess.run(  # noqa: S603
        [
            pwsh_executable,
            "-NoLogo",
            "-NoProfile",
            "-NonInteractive",
            "-File",
            str(verification_script),
        ],
        check=False,
        capture_output=True,
        env=environment,
        text=True,
    )

    assert completed_process.returncode == 0, completed_process.stderr
    assert completed_process.stdout.splitlines() == [
        "ROUTED=pwsh:tools",
        "CALL<activate><--help><>",
        "CALL<activate><tools><extra>",
        "CALL<deactivate><extra><>",
        "CALL<passthrough><two words><>",
        "CALL<fail><><>",
        "STATUS=7",
    ]


@pytest.mark.parametrize("shell_name", list(ShellName))
def test_activation_command_sources_existing_standard_script(
    tmp_path: Path,
    shell_name: ShellName,
) -> None:
    environment_path = tmp_path / "env with space"
    activation_script_path = _create_activation_script(environment_path, shell_name)

    command = render_activation_command(environment_path, shell_name)

    if shell_name.is_posix:
        assert command.startswith("source ")
    else:
        assert command.startswith(". '")
    assert activation_script_path.name in command


def test_activation_command_rejects_missing_standard_script(tmp_path: Path) -> None:
    environment_path = tmp_path / "broken"
    environment_path.mkdir()

    with pytest.raises(UvgError, match="Missing activation script"):
        render_activation_command(environment_path, ShellName.bash)


def test_profile_change_initializes_and_is_idempotent(tmp_path: Path) -> None:
    profile_path = tmp_path / ".bashrc"

    first_change = plan_profile_change(ShellName.bash, profile_path)
    assert first_change.action is ProfileAction.initialize
    assert not profile_path.exists()

    apply_profile_change(first_change)
    second_change = plan_profile_change(ShellName.bash, profile_path)

    assert second_change.action is ProfileAction.no_change
    assert profile_path.read_text(encoding="utf-8").count(start_marker(ShellName.bash)) == 1


def test_profile_change_updates_only_managed_block(tmp_path: Path) -> None:
    profile_path = tmp_path / ".zshrc"
    user_prefix = "# user content before\n\n"
    user_suffix = "# user content after\n"
    stale_block = render_profile_block(ShellName.zsh).replace(
        "command uvg shell hook zsh",
        "command uvg shell hook stale",
    )
    profile_path.write_text(f"{user_prefix}{stale_block}{user_suffix}", encoding="utf-8")

    change = plan_profile_change(ShellName.zsh, profile_path)
    apply_profile_change(change)

    assert change.action is ProfileAction.update
    contents = profile_path.read_text(encoding="utf-8")
    assert contents == f"{user_prefix}{render_profile_block(ShellName.zsh)}{user_suffix}"


def test_profile_remove_is_idempotent(tmp_path: Path) -> None:
    profile_path = tmp_path / ".bashrc"
    user_prefix = "# user content before\n\n"
    user_suffix = "# user content after\n"
    profile_path.write_text(
        f"{user_prefix}{render_profile_block(ShellName.bash)}{user_suffix}",
        encoding="utf-8",
    )

    remove_change = plan_profile_change(ShellName.bash, profile_path, remove=True)
    apply_profile_change(remove_change)
    repeated_change = plan_profile_change(ShellName.bash, profile_path, remove=True)

    assert remove_change.action is ProfileAction.remove
    assert repeated_change.action is ProfileAction.no_change
    assert profile_path.read_text(encoding="utf-8") == f"{user_prefix}{user_suffix}"


def test_profile_rejects_malformed_or_other_shell_markers(tmp_path: Path) -> None:
    profile_path = tmp_path / "profile"
    profile_path.write_text(f"{start_marker(ShellName.zsh)}\n", encoding="utf-8")

    with pytest.raises(UvgError, match="malformed"):
        plan_profile_change(ShellName.zsh, profile_path)

    profile_path.write_text(render_profile_block(ShellName.zsh), encoding="utf-8")
    with pytest.raises(UvgError, match="another shell"):
        plan_profile_change(ShellName.bash, profile_path)


def test_profile_preserves_utf8_bom_crlf_and_mode(tmp_path: Path) -> None:
    profile_path = tmp_path / "profile"
    profile_path.write_bytes(BOM_UTF8 + b"# user\r\n")
    profile_path.chmod(0o640)

    change = plan_profile_change(ShellName.pwsh, profile_path)
    apply_profile_change(change)
    payload = profile_path.read_bytes()

    assert payload.startswith(BOM_UTF8)
    assert b"\r\n" in payload
    assert b"\n" not in payload.replace(b"\r\n", b"")
    if os.name != "nt":
        assert stat.S_IMODE(profile_path.stat().st_mode) == 0o640


def test_profile_rejects_non_utf8_input(tmp_path: Path) -> None:
    profile_path = tmp_path / "profile"
    profile_path.write_bytes(b"\xff\xfe")

    with pytest.raises(UvgError, match="not valid UTF-8"):
        plan_profile_change(ShellName.bash, profile_path)


def test_profile_normalizes_mixed_line_endings_to_crlf(tmp_path: Path) -> None:
    profile_path = tmp_path / "profile"
    profile_path.write_bytes(b"# first\n# second\r\n# third\n")

    change = plan_profile_change(ShellName.bash, profile_path)
    apply_profile_change(change)
    payload = profile_path.read_bytes()

    assert change.action is ProfileAction.initialize
    assert change.line_endings_normalized
    assert b"\r\n" in payload
    assert b"\n" not in payload.replace(b"\r\n", b"")


def test_profile_leaves_bare_cr_characters_untouched(tmp_path: Path) -> None:
    profile_path = tmp_path / "profile"
    profile_path.write_bytes(b"# first\r# second\r")

    change = plan_profile_change(ShellName.bash, profile_path)
    apply_profile_change(change)

    assert change.newline == os.linesep
    assert profile_path.read_bytes().startswith(b"# first\r# second\r")


@pytest.mark.skipif(os.name == "nt", reason="Symlink creation is not generally available")
def test_profile_update_preserves_symlink(tmp_path: Path) -> None:
    target_path = tmp_path / "actual-profile"
    target_path.write_text("# user\n", encoding="utf-8")
    profile_path = tmp_path / ".bashrc"
    profile_path.symlink_to(target_path)

    apply_profile_change(plan_profile_change(ShellName.bash, profile_path))

    assert profile_path.is_symlink()
    assert start_marker(ShellName.bash) in target_path.read_text(encoding="utf-8")


def test_failed_atomic_replace_leaves_original_profile_unchanged(tmp_path: Path) -> None:
    profile_path = tmp_path / ".bashrc"
    original_contents = "# user\n"
    profile_path.write_text(original_contents, encoding="utf-8")
    change = plan_profile_change(ShellName.bash, profile_path)

    with (
        patch("uvg.core.profile.Path.replace", side_effect=OSError("denied")),
        pytest.raises(UvgError, match="Could not update profile"),
    ):
        apply_profile_change(change)

    assert profile_path.read_text(encoding="utf-8") == original_contents
    assert not list(tmp_path.glob(".*.tmp"))


def test_setup_requires_explicit_profile() -> None:
    result = runner.invoke(app, ["setup", "bash"], color=False)
    plain_output = re.sub(r"\x1b\[[0-9;]*m", "", result.output)

    assert result.exit_code == 2
    assert "--profile" in plain_output


def test_setup_dry_run_does_not_create_profile_or_parent(tmp_path: Path) -> None:
    profile_path = tmp_path / "missing" / ".bashrc"

    result = runner.invoke(
        app,
        ["setup", "bash", "--profile", str(profile_path), "--dry-run"],
    )

    assert result.exit_code == 0
    assert "Plan: initialize uvg for bash" in result.output
    assert not profile_path.parent.exists()


def test_setup_reports_line_ending_normalization(tmp_path: Path) -> None:
    profile_path = tmp_path / ".bashrc"
    original_payload = b"# first\n# second\r\n"
    profile_path.write_bytes(original_payload)

    dry_run_result = runner.invoke(
        app,
        ["setup", "bash", "--profile", str(profile_path), "--dry-run"],
    )

    assert dry_run_result.exit_code == 0
    assert "Line endings: normalize to CRLF" in dry_run_result.output
    assert "\r" not in dry_run_result.output
    assert profile_path.read_bytes() == original_payload

    setup_result = runner.invoke(app, ["setup", "bash", "--profile", str(profile_path)])
    payload = profile_path.read_bytes()

    assert setup_result.exit_code == 0
    assert "Normalized line endings: CRLF" in setup_result.output
    assert b"\n" not in payload.replace(b"\r\n", b"")


def test_setup_then_remove_profile_integration(tmp_path: Path) -> None:
    profile_path = tmp_path / ".bashrc"

    setup_result = runner.invoke(
        app,
        ["setup", "bash", "--profile", str(profile_path)],
    )
    remove_result = runner.invoke(
        app,
        ["setup", "bash", "--profile", str(profile_path), "--remove"],
    )

    assert setup_result.exit_code == 0
    assert "Initialized uvg for bash" in setup_result.output
    assert remove_result.exit_code == 0
    assert "Removed uvg for bash" in remove_result.output
    assert start_marker(ShellName.bash) not in profile_path.read_text(encoding="utf-8")


def test_shell_hook_command_writes_only_lf_shell_code() -> None:
    result = runner.invoke(app, ["shell", "hook", "pwsh"])

    assert result.exit_code == 0
    assert result.output.endswith("\n")
    assert "\r" not in result.output
    assert "function global:uvg" in result.output
    assert "_UVG_SHELL_HOOK" not in result.output


def test_shell_activate_writes_code_and_noops_for_active_environment(
    tmp_path: Path,
) -> None:
    environment_path = tmp_path / "venvs" / "tools"
    _create_activation_script(environment_path, ShellName.bash)

    with (
        patch("uvg.commands.shell.resolve_path", return_value=environment_path),
        patch.dict(os.environ, {"VIRTUAL_ENV": str(environment_path)}),
    ):
        result = runner.invoke(app, ["shell", "activate", "bash", "tools"])

    assert result.exit_code == 0
    assert result.output == ":\n"


def test_direct_activate_executable_fails_without_printing_shell_code() -> None:
    result = runner.invoke(app, ["activate", "tools"])

    assert result.exit_code == 1
    assert "cannot modify its parent shell directly" in str(result.exception)
    assert "source " not in result.output


def test_pwsh_activation_layout_matches_platform(tmp_path: Path) -> None:
    activation_path = get_activation_script_path(tmp_path / "tools", ShellName.pwsh)
    expected_parts = ("Scripts", "Activate.ps1") if IS_WINDOWS else ("bin", "activate.ps1")

    assert activation_path.parts[-2:] == expected_parts


@pytest.mark.skipif(
    os.name != "nt" or GIT_BASH_EXECUTABLE is None,
    reason="Git Bash is unavailable",
)
def test_windows_git_bash_loads_new_crlf_profile(tmp_path: Path) -> None:
    assert GIT_BASH_EXECUTABLE is not None
    uvg_home, environment_path = _create_uv_environment(tmp_path)
    profile_path = tmp_path / ".bashrc"
    change = plan_profile_change(ShellName.bash, profile_path)
    apply_profile_change(change)
    payload = profile_path.read_bytes()

    assert change.newline == "\r\n"
    assert b"\n" not in payload.replace(b"\r\n", b"")

    rendered_profile_path = render_path_for_shell(profile_path, ShellName.bash)
    environment = _environment_with_current_scripts_on_path()
    environment["UVG_HOME"] = str(uvg_home)
    completed_process = subprocess.run(  # noqa: S603
        [
            GIT_BASH_EXECUTABLE,
            "--noprofile",
            "--norc",
            "-c",
            " && ".join(
                [
                    f"source {shlex.quote(rendered_profile_path)}",
                    "type -t uvg",
                    "uvg --version",
                    "uvg activate tools",
                    'printf "ACTIVE=%s\n" "$(cygpath -w "$VIRTUAL_ENV")"',
                    "python -c 'import sys; print(\"PREFIX=\" + sys.prefix)'",
                    "uvg deactivate",
                    'printf "INACTIVE=%s\n" "${VIRTUAL_ENV-}"',
                ],
            ),
        ],
        check=False,
        capture_output=True,
        env=environment,
        text=True,
    )

    assert completed_process.returncode == 0, completed_process.stderr
    output_lines = completed_process.stdout.splitlines()
    assert output_lines[0] == "function"
    assert f"ACTIVE={environment_path}" in output_lines
    prefix_line = next(line for line in output_lines if line.startswith("PREFIX="))
    assert os.path.normcase(os.path.normpath(prefix_line.removeprefix("PREFIX="))) == (
        os.path.normcase(os.path.normpath(environment_path))
    )
    assert output_lines[-1] == "INACTIVE="


@pytest.mark.skipif(shutil.which("pwsh") is None, reason="PowerShell 7 is unavailable")
def test_pwsh_loader_activates_and_deactivates_in_real_shell(tmp_path: Path) -> None:
    pwsh_executable = shutil.which("pwsh")
    assert pwsh_executable is not None
    uvg_home, environment_path = _create_uv_environment(tmp_path)
    profile_path = tmp_path / "profile.ps1"
    profile_path.write_text(render_profile_block(ShellName.pwsh), encoding="utf-8")
    verification_script = tmp_path / "verify.ps1"
    verification_script.write_text(
        "\n".join(
            [
                f". {quote_pwsh_string_literal(str(profile_path))}",
                "uvg activate tools",
                '[Console]::Out.WriteLine("ACTIVE=" + $env:VIRTUAL_ENV)',
                (
                    '[Console]::Out.WriteLine("PYTHON=" + '
                    "(Get-Command python -CommandType Application -TotalCount 1).Source)"
                ),
                "uvg deactivate",
                '[Console]::Out.WriteLine("INACTIVE=" + $env:VIRTUAL_ENV)',
            ],
        ),
        encoding="utf-8",
    )
    environment = _environment_with_current_scripts_on_path()
    environment["UVG_HOME"] = str(uvg_home)

    completed_process = subprocess.run(  # noqa: S603
        [
            pwsh_executable,
            "-NoLogo",
            "-NoProfile",
            "-NonInteractive",
            "-File",
            str(verification_script),
        ],
        check=False,
        capture_output=True,
        env=environment,
        text=True,
    )

    assert completed_process.returncode == 0, completed_process.stderr
    assert f"ACTIVE={environment_path}" in completed_process.stdout
    python_line = next(
        line for line in completed_process.stdout.splitlines() if line.startswith("PYTHON=")
    )
    expected_python_path = environment_path / (
        Path("Scripts/python.exe") if IS_WINDOWS else Path("bin/python")
    )
    assert os.path.normcase(os.path.normpath(python_line.removeprefix("PYTHON="))) == (
        os.path.normcase(os.path.normpath(expected_python_path))
    )
    assert "INACTIVE=\n" in completed_process.stdout.replace("\r\n", "\n")


@pytest.mark.skipif(os.name == "nt", reason="POSIX shell executable test")
@pytest.mark.parametrize(
    ("shell_name", "executable_name", "shell_arguments"),
    POSIX_SHELL_CASES,
)
def test_posix_loader_activates_and_deactivates_in_real_shell(
    tmp_path: Path,
    shell_name: ShellName,
    executable_name: str,
    shell_arguments: tuple[str, ...],
) -> None:
    shell_executable = shutil.which(executable_name)
    if shell_executable is None:
        pytest.skip(f"{executable_name} is unavailable")
    uvg_home, environment_path = _create_uv_environment(tmp_path)
    profile_path = tmp_path / f"profile.{shell_name.value}"
    profile_path.write_text(render_profile_block(shell_name), encoding="utf-8")
    verification_script = tmp_path / f"verify.{shell_name.value}"
    verification_script.write_text(
        "\n".join(
            [
                "set -e",
                f"source {shlex.quote(str(profile_path))}",
                "uvg activate tools",
                'printf "ACTIVE=%s\\n" "$VIRTUAL_ENV"',
                'printf "PYTHON=%s\\n" "$(command -v python)"',
                "uvg deactivate",
                'printf "INACTIVE=%s\\n" "${VIRTUAL_ENV-}"',
            ],
        ),
        encoding="utf-8",
    )
    environment = _environment_with_current_scripts_on_path()
    environment["UVG_HOME"] = str(uvg_home)

    completed_process = subprocess.run(  # noqa: S603
        [shell_executable, *shell_arguments, str(verification_script)],
        check=False,
        capture_output=True,
        env=environment,
        text=True,
    )

    assert completed_process.returncode == 0, completed_process.stderr
    assert f"ACTIVE={environment_path}" in completed_process.stdout
    assert f"PYTHON={environment_path / 'bin' / 'python'}" in completed_process.stdout
    assert "INACTIVE=\n" in completed_process.stdout
