from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from uvg.shell import (
    append_shell_integration_to_profile,
    build_activation_script_path,
    render_activation_command,
    render_shell_integration_script,
)


class ShellIntegrationTests(unittest.TestCase):
    def test_render_shell_integration_script_uses_cli_composition_for_activation(
        self,
    ) -> None:
        shell_script = render_shell_integration_script("bash")

        self.assertIn(
            'activation_command="$(command uvg activate --shell bash "$2")"',
            shell_script,
        )
        self.assertIn('eval "$activation_command"', shell_script)

    def test_append_shell_integration_to_profile_is_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            profile_path = Path(temporary_directory) / ".bashrc"

            first_write_result = append_shell_integration_to_profile(
                "bash", profile_path
            )
            second_write_result = append_shell_integration_to_profile(
                "bash", profile_path
            )

            self.assertTrue(first_write_result)
            self.assertFalse(second_write_result)

    @patch("uvg.shell.platform.system", return_value="Windows")
    def test_render_activation_command_returns_posix_source_command_for_bash_on_windows(
        self,
        platform_system_mock,
    ) -> None:
        activation_command = render_activation_command(
            Path(r"C:\Users\me\.uvg\venvs\tools"), "bash"
        )

        self.assertEqual(
            activation_command,
            "source C:/Users/me/.uvg/venvs/tools/Scripts/activate",
        )
        platform_system_mock.assert_called()

    @patch("uvg.shell.platform.system", return_value="Windows")
    def test_render_activation_command_returns_pwsh_dot_source_command(
        self,
        platform_system_mock,
    ) -> None:
        activation_command = render_activation_command(
            Path(r"C:\Users\me\.uvg\venvs\tools"), "ps1"
        )

        self.assertEqual(
            activation_command,
            ". 'C:\\Users\\me\\.uvg\\venvs\\tools\\Scripts\\Activate.ps1'",
        )
        platform_system_mock.assert_called()

    @patch("uvg.shell.platform.system", return_value="Windows")
    def test_build_activation_script_path_uses_scripts_directory_for_bash_on_windows(
        self,
        platform_system_mock,
    ) -> None:
        activation_script_path = build_activation_script_path(
            Path(r"C:\Users\me\.uvg\venvs\tools"),
            "bash",
        )

        self.assertEqual(
            activation_script_path,
            "C:/Users/me/.uvg/venvs/tools/Scripts/activate",
        )
        platform_system_mock.assert_called()
