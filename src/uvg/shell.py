from __future__ import annotations

import platform
import shlex
from pathlib import Path, PureWindowsPath
from typing import Literal


ShellType = Literal["bash", "zsh", "ps1", "pwsh"]


# ============================================================================
# Constants
# ============================================================================

PROFILE_SNIPPET_START_MARKER = "# >>> uvg initialize >>>"
PROFILE_SNIPPET_END_MARKER = "# <<< uvg initialize <<<"


# ============================================================================
# Shell Detection
# ============================================================================


def get_default_shell_type_for_current_platform() -> ShellType:
    """Get the default shell type for the current operating system."""
    if platform.system() == "Windows":
        return "ps1"
    return "bash"


# ============================================================================
# Script Generation
# ============================================================================


def render_shell_integration_script(shell_name: ShellType) -> str:
    """Render the shell integration script for a specific shell."""
    if shell_name == "bash" or shell_name == "zsh":
        # TODO(ty): 使用 list 没有达到 Type Narrowing 的效果，暂时先用 == 了
        return _render_posix_shell_integration_script(shell_name)

    if shell_name == "ps1" or shell_name == "pwsh":
        # TODO(ty): 使用 list 没有达到 Type Narrowing 的效果，暂时先用 == 了
        return _render_pwsh_integration_script()

    raise ValueError(f"Unsupported shell: {shell_name}")


def _render_posix_shell_integration_script(shell_name: Literal["bash", "zsh"]) -> str:
    """Render shell integration script for bash/zsh."""
    # TODO: 目前没有实际测试过这些能否生效
    return f"""# uvg shell integration for bash/zsh
uvg() {{
    if [ "$1" = "activate" ]; then
        if [ -z "$2" ]; then
            echo "Error: Please specify an environment name." >&2
            return 1
        fi

        local activation_command
        activation_command="$(command uvg activate --shell {shell_name} "$2")" || return 1
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
        $activationCommand = & $uvgExecutable activate --shell ps1 $args[1]
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
    shell_name: ShellType, profile_path: Path
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
    with profile_path.open("a", encoding="utf-8") as profile_file:
        profile_file.write(profile_snippet)

    return True


def build_profile_initialization_command(shell_name: ShellType) -> str:
    """Build the initialization command for a shell profile."""
    if shell_name in {"ps1", "pwsh"}:
        return "Invoke-Expression (uvg init ps1 | Out-String)"
    if shell_name == "bash":
        return 'eval "$(uvg init bash)"'
    return 'eval "$(uvg init zsh)"'


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


def render_activation_command(environment_path: Path, shell_name: ShellType) -> str:
    """Render the command to activate an environment for a specific shell."""
    activation_script_path = build_activation_script_path(environment_path, shell_name)

    if shell_name in {"bash", "zsh"}:
        return f"source {shlex.quote(activation_script_path)}"

    return f". {_quote_pwsh_string_literal(activation_script_path)}"


def build_activation_script_path(environment_path: Path, shell_name: ShellType) -> str:
    """Build the path to the activation script for a shell."""
    if platform.system() == "Windows":
        if shell_name in {"bash", "zsh"}:
            return PureWindowsPath(environment_path, "Scripts", "activate").as_posix()
        return str(PureWindowsPath(environment_path, "Scripts", "Activate.ps1"))

    if shell_name in {"bash", "zsh"}:
        return str(environment_path / "bin" / "activate")

    return str(environment_path / "bin" / "Activate.ps1")


def _quote_pwsh_string_literal(value: str) -> str:
    """Quote a string for Pwsh."""
    return "'" + value.replace("'", "''") + "'"
