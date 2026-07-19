"""Shell code generation for uvg integration."""

from __future__ import annotations

import shlex
import sys
from enum import StrEnum
from typing import TYPE_CHECKING

from uvg.core.errors import UvgError

if TYPE_CHECKING:
    from pathlib import Path


class ShellName(StrEnum):
    """Shells supported by uvg integration helpers."""

    bash = "bash"
    zsh = "zsh"
    pwsh = "pwsh"

    @property
    def is_posix(self) -> bool:
        """Return whether this shell uses POSIX syntax."""
        return self in {ShellName.bash, ShellName.zsh}


IS_WINDOWS = sys.platform == "win32"


def render_profile_loader(shell_name: ShellName) -> str:
    """Render the dynamic loader installed in a shell profile."""
    if shell_name.is_posix:
        return _render_posix_profile_loader(shell_name)
    return _render_pwsh_profile_loader()


def render_shell_hook(shell_name: ShellName) -> str:
    """Render the complete runtime hook for a shell."""
    if shell_name.is_posix:
        return _render_posix_shell_hook(shell_name)
    return _render_pwsh_shell_hook()


def render_activation_command(environment_path: Path, shell_name: ShellName) -> str:
    """Render code that sources the environment's standard activation script."""
    activation_script_path = get_activation_script_path(environment_path, shell_name)
    if not activation_script_path.is_file():
        raise UvgError(
            f"Environment '{environment_path.name}' is invalid.\n"
            f"Missing activation script:\n  {activation_script_path}",
        )

    rendered_path = render_path_for_shell(activation_script_path, shell_name)
    if shell_name.is_posix:
        return f"source {shlex.quote(rendered_path)}"
    return f". {_quote_pwsh_string_literal(rendered_path)}"


def get_activation_script_path(environment_path: Path, shell_name: ShellName) -> Path:
    """Return the native path to an environment activation script."""
    scripts_directory = environment_path / ("Scripts" if IS_WINDOWS else "bin")
    if shell_name.is_posix:
        script_name = "activate"
    else:
        script_name = "Activate.ps1" if IS_WINDOWS else "activate.ps1"
    return scripts_directory / script_name


def render_path_for_shell(path: Path, shell_name: ShellName) -> str:
    """Render a native path in the syntax expected by a target shell."""
    if IS_WINDOWS and shell_name.is_posix:
        return convert_windows_path_to_msys_path(path)
    return str(path)


def convert_windows_path_to_msys_path(path: Path) -> str:
    """Convert a Windows drive path to an MSYS-style path."""
    posix_path = path.as_posix()
    drive = path.drive
    if drive.endswith(":"):
        return f"/{drive[:-1].lower()}{posix_path.removeprefix(drive)}"
    return posix_path


def quote_pwsh_string_literal(value: str) -> str:
    """Quote a string as a PowerShell single-quoted literal."""
    return _quote_pwsh_string_literal(value)


def _render_posix_profile_loader(shell_name: ShellName) -> str:
    return f"""_uvg_hook=
if _uvg_hook="$(command uvg shell hook {shell_name.value})"; then
    if [ -n "$_uvg_hook" ]; then
        eval "$_uvg_hook" || printf '%s\\n' "uvg: failed to load {shell_name.value} hook" >&2
    else
        printf '%s\\n' "uvg: generated an empty {shell_name.value} hook" >&2
    fi
fi
unset _uvg_hook"""


def _render_pwsh_profile_loader() -> str:
    return """$uvgCommand = Get-Command uvg -CommandType Application `
    -TotalCount 1 -ErrorAction SilentlyContinue
if ($null -eq $uvgCommand) {
    Write-Error "uvg executable was not found on PATH."
} else {
    $uvgHook = & $uvgCommand.Source shell hook pwsh
    if ($LASTEXITCODE -eq 0) {
        $uvgHookText = $uvgHook -join "`n"
        if ([string]::IsNullOrWhiteSpace($uvgHookText)) {
            Write-Error "uvg generated an empty PowerShell hook."
        } else {
            Invoke-Expression $uvgHookText
            if (-not $?) {
                Write-Error "uvg failed to load the PowerShell hook."
            }
        }
    }
}
Remove-Variable uvgCommand, uvgHook, uvgHookText -ErrorAction SilentlyContinue"""


def _render_posix_shell_hook(shell_name: ShellName) -> str:
    return f"""uvg() {{
    if [ "$#" -eq 2 ] && [ "$1" = "activate" ] && [ "$2" != "--help" ] && [ "$2" != "-h" ]; then
        local activation_code
        activation_code="$(command uvg shell activate {shell_name.value} "$2")" || return $?
        if [ -z "$activation_code" ]; then
            echo "Error: uvg returned empty activation code." >&2
            return 1
        fi
        eval "$activation_code"
        return $?
    fi

    if [ "$#" -eq 1 ] && [ "$1" = "deactivate" ]; then
        if command -v deactivate >/dev/null 2>&1; then
            deactivate
            return $?
        fi
        echo "Error: no virtual environment is active." >&2
        return 1
    fi

    command uvg "$@"
}}"""


def _render_pwsh_shell_hook() -> str:
    return """function global:uvg {
    $originalArguments = @($args)
    $uvgCommand = Get-Command uvg -CommandType Application `
        -TotalCount 1 -ErrorAction SilentlyContinue
    if ($null -eq $uvgCommand) {
        Write-Error "uvg executable was not found on PATH."
        $global:LASTEXITCODE = 1
        return
    }
    $uvgExecutable = $uvgCommand.Source

    if (
        $originalArguments.Count -eq 2 -and
        $originalArguments[0] -eq "activate" -and
        $originalArguments[1] -notin @("--help", "-h")
    ) {
        $activationCode = & $uvgExecutable shell activate pwsh ([string]$originalArguments[1])
        if ($LASTEXITCODE -ne 0) {
            return
        }
        if ([string]::IsNullOrWhiteSpace(($activationCode -join "`n"))) {
            Write-Error "uvg returned empty activation code."
            $global:LASTEXITCODE = 1
            return
        }
        Invoke-Expression ($activationCode -join "`n")
        if ($?) {
            $global:LASTEXITCODE = 0
        } else {
            $global:LASTEXITCODE = 1
        }
        return
    }

    if ($originalArguments.Count -eq 1 -and $originalArguments[0] -eq "deactivate") {
        if (Test-Path Function:\\deactivate) {
            deactivate
            $global:LASTEXITCODE = 0
        } else {
            Write-Error "No virtual environment is active."
            $global:LASTEXITCODE = 1
        }
        return
    }

    & $uvgExecutable @originalArguments
}"""


def _quote_pwsh_string_literal(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"
