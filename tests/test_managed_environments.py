from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import uvg.environment as environment_module
from uvg.errors import UvgError
from uvg.environment import (
    validate_managed_environment_name,
    list_managed_environment_names,
    remove_managed_environment,
    current_environment_name,
    create_managed_environment,
)


class ManagedEnvironmentTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)

        self.uvg_home_directory = Path(self.temporary_directory.name) / ".uvg"
        self.managed_environments_directory = self.uvg_home_directory / "venvs"

        self.uvg_home_patcher = patch.object(
            environment_module,
            "UVG_HOME_DIRECTORY",
            self.uvg_home_directory,
        )
        self.environment_directory_patcher = patch.object(
            environment_module,
            "MANAGED_ENVIRONMENTS_DIRECTORY",
            self.managed_environments_directory,
        )
        self.uvg_home_patcher.start()
        self.environment_directory_patcher.start()
        self.addCleanup(self.uvg_home_patcher.stop)
        self.addCleanup(self.environment_directory_patcher.stop)

    def test_validate_managed_environment_name_rejects_path_traversal(self) -> None:
        with self.assertRaises(UvgError):
            validate_managed_environment_name("../tools")

    def test_list_managed_environment_names_returns_sorted_names(self) -> None:
        (self.managed_environments_directory / "zeta").mkdir(parents=True)
        (self.managed_environments_directory / "alpha").mkdir()

        self.assertEqual(list_managed_environment_names(), ["alpha", "zeta"])

    @patch("uvg.environment.subprocess.run")
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

        environment_path = create_managed_environment("tools", "3.12")

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

    @patch("uvg.environment.subprocess.run", side_effect=FileNotFoundError)
    def test_create_managed_environment_reports_missing_uv_executable(
        self,
        subprocess_run_mock,
    ) -> None:
        with self.assertRaisesRegex(UvgError, "The `uv` executable was not found"):
            create_managed_environment("tools")

    @patch.dict("os.environ", {}, clear=True)
    def test_current_environment_name_returns_none_when_silent_without_active_environment(
        self,
    ) -> None:
        self.assertIsNone(current_environment_name(silent=True))

    @patch("uvg.environment.current_environment_name", return_value="tools")
    def test_remove_managed_environment_refuses_active_environment(
        self,
        current_environment_name_mock,
    ) -> None:
        (self.managed_environments_directory / "tools").mkdir(parents=True)

        with self.assertRaisesRegex(UvgError, "currently active"):
            remove_managed_environment("tools")

        current_environment_name_mock.assert_called_once_with(silent=True)
