from __future__ import annotations

import sys
import tempfile
import unittest
from io import BytesIO
from pathlib import Path
from unittest.mock import MagicMock, patch

from uvg.commands.activate import activate_environment_command
from uvg.commands.init import initialize_shell_integration_command
from uvg.core.shell import (
    ShellName,
    append_shell_integration_to_profile,
    build_activation_script_path,
    render_activation_command,
    render_shell_integration_script,
)


class BinaryStdout:
    def __init__(self) -> None:
        self.buffer = BytesIO()


class ShellIntegrationTests(unittest.TestCase):
    def test_render_shell_integration_script_uses_cli_composition_for_activation(
        self,
    ) -> None:
        shell_script = render_shell_integration_script(ShellName.bash)

        assert 'activation_command="$(command uvg activate --shell bash "$2")"' in shell_script
        assert 'eval "$activation_command"' in shell_script

    def test_append_shell_integration_to_profile_is_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            profile_path = Path(temporary_directory) / ".bashrc"

            first_write_result = append_shell_integration_to_profile(
                ShellName.bash,
                profile_path,
            )
            second_write_result = append_shell_integration_to_profile(
                ShellName.bash,
                profile_path,
            )

            assert first_write_result
            assert not second_write_result

    @unittest.skipUnless(sys.platform == "win32", "Windows-only path rendering")
    def test_render_activation_command_returns_posix_source_command_for_bash_on_windows(
        self,
    ) -> None:
        activation_command = render_activation_command(
            Path(r"C:\Users\me\.uvg\venvs\tools"),
            ShellName.bash,
        )

        assert activation_command == "source /c/Users/me/.uvg/venvs/tools/Scripts/activate"

    @unittest.skipUnless(sys.platform == "win32", "Windows-only path rendering")
    def test_render_activation_command_returns_pwsh_dot_source_command(self) -> None:
        activation_command = render_activation_command(
            Path(r"C:\Users\me\.uvg\venvs\tools"),
            ShellName.pwsh,
        )

        assert activation_command == ". 'C:\\Users\\me\\.uvg\\venvs\\tools\\Scripts\\Activate.ps1'"

    @unittest.skipUnless(sys.platform == "win32", "Windows-only path rendering")
    def test_build_activation_script_path_uses_scripts_directory_for_bash_on_windows(
        self,
    ) -> None:
        activation_script_path = build_activation_script_path(
            Path(r"C:\Users\me\.uvg\venvs\tools"),
            ShellName.bash,
        )

        assert activation_script_path == "/c/Users/me/.uvg/venvs/tools/Scripts/activate"

    @patch("uvg.commands.activate.resolve_path")
    def test_activate_command_writes_shell_code_with_binary_stdout(
        self,
        resolve_path_mock: MagicMock,
    ) -> None:
        resolve_path_mock.return_value = Path(r"C:\Users\me\.uvg\venvs\tools")

        for shell_name in (ShellName.bash, ShellName.pwsh):
            with self.subTest(shell_name=shell_name):
                stdout = BinaryStdout()
                with patch("uvg.commands.activate.sys.stdout", stdout):
                    activate_environment_command("tools", shell_name)

                output = stdout.buffer.getvalue()
                assert output.endswith(b"\n")
                assert b"\r" not in output

    def test_init_command_writes_shell_code_with_binary_stdout(self) -> None:
        for shell_name in (ShellName.bash, ShellName.pwsh):
            with self.subTest(shell_name=shell_name):
                stdout = BinaryStdout()
                with patch("uvg.commands.init.sys.stdout", stdout):
                    initialize_shell_integration_command(shell_name)

                output = stdout.buffer.getvalue()
                assert output.endswith(b"\n")
                assert b"\r" not in output
