"""Shell code generation for uvg integration."""

from __future__ import annotations

import shlex
import sys
from enum import StrEnum
from typing import TYPE_CHECKING

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


def render_shell_hook(shell_name: ShellName) -> str:
    """Render the complete runtime hook for a shell."""
    if shell_name.is_posix:
        return _render_posix_shell_hook(shell_name)
    return _render_pwsh_shell_hook()


def render_activation_command(activation_script_path: Path, shell_name: ShellName) -> str:
    """Render code to source a located script without accessing the filesystem."""
    rendered_path = render_path_for_shell(activation_script_path, shell_name)
    if shell_name.is_posix:
        return f"source {shlex.quote(rendered_path)}"
    return f". {quote_pwsh_string_literal(rendered_path)}"


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
    return "'" + value.replace("'", "''") + "'"


def _render_posix_shell_hook(shell_name: ShellName) -> str:
    return f"""uvg() {{
    if [ "$#" -eq 2 ] && [ "$1" = "activate" ] && [ "${{2#-}}" = "$2" ]; then
        local activation_code
        activation_code="$(command uvg shell activate {shell_name.value} "$2")" &&
            eval "$activation_code"
    elif [ "$#" -eq 1 ] && [ "$1" = "deactivate" ]; then
        if typeset -f deactivate >/dev/null 2>&1; then
            deactivate
        else
            printf '%s\\n' "uvg: no active environment" >&2
            return 1
        fi
    else
        command uvg "$@"
    fi
}}"""


def _render_pwsh_shell_hook() -> str:
    return """function global:uvg {
    if ($args.Count -eq 1 -and $args[0] -eq "deactivate") {
        if (Test-Path Function:\\deactivate) {
            try {
                deactivate
                $global:LASTEXITCODE = [int](-not $?)
            } catch {
                $global:LASTEXITCODE = 1
                Write-Error -ErrorRecord $_
            }
        } else {
            $global:LASTEXITCODE = 1
            Write-Error "uvg: no active environment"
        }
        return
    }

    $uvgCommand = Get-Command uvg -CommandType Application `
        -TotalCount 1 -ErrorAction SilentlyContinue
    if ($null -eq $uvgCommand) {
        $global:LASTEXITCODE = 1
        Write-Error "uvg executable was not found on PATH."
        return
    }
    if (
        $args.Count -eq 2 -and
        $args[0] -eq "activate" -and
        -not ([string]$args[1]).StartsWith("-")
    ) {
        $activationCode = & $uvgCommand.Source shell activate pwsh $args[1]
        if ($LASTEXITCODE -ne 0) {
            return
        }
        try {
            Invoke-Expression ($activationCode -join "`n") -ErrorAction Stop
            $global:LASTEXITCODE = [int](-not $?)
        } catch {
            $global:LASTEXITCODE = 1
            Write-Error -ErrorRecord $_
        }
        return
    }

    & $uvgCommand.Source @args
}"""
