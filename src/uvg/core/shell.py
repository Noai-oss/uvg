from __future__ import annotations

import shlex
import sys
from enum import Enum
from pathlib import Path
from typing import Literal, TypeAlias


class ShellName(str, Enum):
    bash = "bash"
    zsh = "zsh"
    pwsh = "pwsh"

    @property
    def is_posix(self) -> bool:
        return self in {ShellName.bash, ShellName.zsh}


PosixShellName: TypeAlias = Literal[ShellName.bash, ShellName.zsh]

IS_WINDOWS = sys.platform == "win32"


# ============================================================================
# Constants
# ============================================================================

PROFILE_SNIPPET_START_MARKER = "# >>> uvg initialize >>>"
PROFILE_SNIPPET_END_MARKER = "# <<< uvg initialize <<<"


# ============================================================================
# Shell Detection
# ============================================================================


def get_default_shell_type_for_current_platform() -> ShellName:
    """Get the default shell type for the current operating system."""
    return ShellName.pwsh if IS_WINDOWS else ShellName.bash


# ============================================================================
# Script Generation
# ============================================================================


def render_shell_integration_script(shell_name: ShellName) -> str:
    """Render the shell integration script for a specific shell."""
    match shell_name:
        case ShellName.pwsh:
            return _render_pwsh_integration_script()
        case ShellName.bash | ShellName.zsh:
            return _render_posix_shell_integration_script(shell_name)
        case _:
            raise ValueError(f"Unsupported shell: {shell_name}")


def _render_posix_shell_integration_script(
    shell_name: PosixShellName,
) -> str:
    """Render shell integration script for POSIX-style shells."""
    return f"""# uvg shell integration for {shell_name.value}
uvg() {{
    if [ "$1" = "activate" ]; then
        if [ -z "$2" ]; then
            echo "Error: Please specify an environment name." >&2
            return 1
        fi

        local activation_command
        activation_command="$(command uvg activate --shell {shell_name.value} "$2")" || return 1
        eval "$activation_command"
        return $?
    fi

    command uvg "$@"
}}"""


def _render_pwsh_integration_script() -> str:
    """Render shell integration script for Pwsh."""
    return r"""# uvg shell integration for Pwsh
function uvg {
    if ($args[0] -eq "activate") {
        if ($args.Count -lt 2 -or [string]::IsNullOrWhiteSpace($args[1])) {
            Write-Error "Please specify an environment name."
            $global:LASTEXITCODE = 1
            return
        }

        $uvgExecutable = (Get-Command uvg -CommandType Application -TotalCount 1).Source
        $activationCommand = & $uvgExecutable activate --shell pwsh $args[1]
        if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($activationCommand)) {
            $global:LASTEXITCODE = 1
            return
        }

        Invoke-Expression $activationCommand
        return
    }

    $uvgExecutable = (Get-Command uvg -CommandType Application -TotalCount 1).Source
    & $uvgExecutable @args
}"""


# ============================================================================
# Profile Integration
# ============================================================================


def append_shell_integration_to_profile(
    shell_name: ShellName, profile_path: Path
) -> bool:
    """Append shell integration snippet to a shell profile file."""
    initialization_command = build_profile_initialization_command(shell_name)
    profile_snippet = render_profile_initialization_snippet(initialization_command)

    if profile_path.exists():
        current_profile_contents = profile_path.read_text(encoding="utf-8")
        if (
            PROFILE_SNIPPET_START_MARKER in current_profile_contents
            or initialization_command in current_profile_contents
        ):
            return False

    profile_path.parent.mkdir(parents=True, exist_ok=True)
    with profile_path.open("a", encoding="utf-8", newline="\n") as profile_file:
        profile_file.write(profile_snippet)

    return True


def build_profile_initialization_command(shell_name: ShellName) -> str:
    """Build the initialization command for a shell profile."""
    match shell_name:
        case ShellName.pwsh:
            return "Invoke-Expression (uvg init pwsh | Out-String)"
        case ShellName.bash:
            return 'eval "$(uvg init bash)"'
        case ShellName.zsh:
            return 'eval "$(uvg init zsh)"'
        case _:
            raise ValueError(f"Unsupported shell: {shell_name}")


def render_profile_initialization_snippet(initialization_command: str) -> str:
    """Render the profile initialization snippet with markers."""
    return (
        "\n"
        f"{PROFILE_SNIPPET_START_MARKER}\n"
        f"{initialization_command}\n"
        f"{PROFILE_SNIPPET_END_MARKER}\n"
    )


# ============================================================================
# Activation
# ============================================================================


def render_activation_command(environment_path: Path, shell_name: ShellName) -> str:
    """Render the command to activate an environment for a specific shell."""
    activation_script_path = build_activation_script_path(environment_path, shell_name)

    if shell_name in {ShellName.bash, ShellName.zsh}:
        return f"source {shlex.quote(activation_script_path)}"

    return f". {_quote_pwsh_string_literal(activation_script_path)}"


def build_activation_script_path(environment_path: Path, shell_name: ShellName) -> str:
    """Build the path to the activation script for a shell."""
    scripts_dir = environment_path / ("Scripts" if IS_WINDOWS else "bin")

    if shell_name in {ShellName.bash, ShellName.zsh}:
        script_path = scripts_dir / "activate"
        return (
            convert_windows_path_to_msys_path(script_path)
            if IS_WINDOWS
            else str(script_path)
        )

    return str(scripts_dir / "Activate.ps1")


def _quote_pwsh_string_literal(value: str) -> str:
    """Quote a string for Pwsh."""
    return "'" + value.replace("'", "''") + "'"


def convert_windows_path_to_msys_path(path: Path) -> str:
    """Convert C:/style paths to /c/style paths for MSYS-like shells."""
    posix_path = path.as_posix()
    if len(posix_path) >= 3 and posix_path[1:3] == ":/":
        return f"/{posix_path[0].lower()}{posix_path[2:]}"
    return posix_path
