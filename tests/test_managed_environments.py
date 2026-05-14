from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import uvg.core.environment as environment_module
from uvg.cli.env import list_environments_command
from uvg.core.errors import UvgError
from uvg.core.environment import (
    create,
    get_current_name,
    list_names,
    read_python_version,
    remove,
    validate_name,
)


class ManagedEnvironmentTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)

        self.uvg_home_directory = Path(self.temporary_directory.name) / ".uvg"
        self.managed_environments_directory = self.uvg_home_directory / "venvs"

        self.uvg_home_patcher = patch.object(
            environment_module,
            "UVG_HOME_DIR",
            self.uvg_home_directory,
        )
        self.environment_directory_patcher = patch.object(
            environment_module,
            "VENVS_DIR",
            self.managed_environments_directory,
        )
        self.uvg_home_patcher.start()
        self.environment_directory_patcher.start()
        self.addCleanup(self.uvg_home_patcher.stop)
        self.addCleanup(self.environment_directory_patcher.stop)

    def test_validate_managed_environment_name_rejects_path_traversal(self) -> None:
        with self.assertRaises(UvgError):
            validate_name("../tools")

    def test_list_managed_environment_names_returns_sorted_names(self) -> None:
        (self.managed_environments_directory / "zeta").mkdir(parents=True)
        (self.managed_environments_directory / "alpha").mkdir()

        self.assertEqual(list_names(), ["alpha", "zeta"])

    def test_read_python_version_reads_pyvenv_cfg_version_info(self) -> None:
        environment_path = self.managed_environments_directory / "tools"
        environment_path.mkdir(parents=True)
        (environment_path / "pyvenv.cfg").write_text(
            "version_info = 3.14.0rc3\n",
            encoding="utf-8",
        )

        self.assertEqual(read_python_version(environment_path), "3.14.0rc3")

    def test_list_managed_environments_prints_name_and_version_without_header(
        self,
    ) -> None:
        alpha_environment_path = self.managed_environments_directory / "alpha"
        zeta_environment_path = self.managed_environments_directory / "zeta"
        alpha_environment_path.mkdir(parents=True)
        zeta_environment_path.mkdir()
        (alpha_environment_path / "pyvenv.cfg").write_text(
            "version_info = 3.12.11\n",
            encoding="utf-8",
        )

        printed_lines: list[str] = []
        with patch("uvg.cli.env.typer.echo", side_effect=printed_lines.append):
            list_environments_command()

        self.assertEqual(printed_lines, ["alpha  3.12.11", "zeta   unknown"])

    @patch("uvg.core.environment.subprocess.run")
    def test_create_managed_environment_invokes_uv_with_expected_arguments(
        self,
        subprocess_run_mock,
    ) -> None:
        subprocess_run_mock.return_value = subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout="",
            stderr="",
        )

        environment_path = create("tools", "3.12")

        self.assertEqual(
            environment_path, self.managed_environments_directory / "tools"
        )
        subprocess_run_mock.assert_called_once_with(
            [
                "uv",
                "venv",
                str(self.managed_environments_directory / "tools"),
                "--seed",
                "--python",
                "3.12",
            ],
            capture_output=True,
            check=False,
            text=True,
        )

    @patch("uvg.core.environment.subprocess.run", side_effect=FileNotFoundError)
    def test_create_managed_environment_reports_missing_uv_executable(
        self,
        subprocess_run_mock,
    ) -> None:
        with self.assertRaisesRegex(UvgError, "The `uv` executable was not found"):
            create("tools")

    @patch.dict("os.environ", {}, clear=True)
    def test_current_environment_name_returns_none_when_silent_without_active_environment(
        self,
    ) -> None:
        self.assertIsNone(get_current_name(silent=True))

    @patch("uvg.core.environment.get_current_name", return_value="tools")
    def test_remove_managed_environment_refuses_active_environment(
        self,
        current_environment_name_mock,
    ) -> None:
        (self.managed_environments_directory / "tools").mkdir(parents=True)

        with self.assertRaisesRegex(UvgError, "currently active"):
            remove("tools")

        current_environment_name_mock.assert_called_once_with(silent=True)
