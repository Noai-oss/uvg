from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import typer

from uvg.commands.create import create_environment_command
from uvg.commands.env.list import list_environments_command
from uvg.commands.remove import remove_environment_command
from uvg.core.environment import (
    create,
    get_current_name,
    get_venvs_dir,
    list_names,
    read_python_version,
    remove,
    validate_name,
)
from uvg.core.errors import UvgError


class ManagedEnvironmentTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)

        self.uvg_home_directory = Path(self.temporary_directory.name) / ".uvg"
        self.managed_environments_directory = self.uvg_home_directory / "venvs"

        self.environment_patcher = patch.dict(
            "os.environ",
            {"UVG_HOME": str(self.uvg_home_directory)},
        )
        self.environment_patcher.start()
        self.addCleanup(self.environment_patcher.stop)

    def test_validate_managed_environment_name_rejects_path_traversal(self) -> None:
        with pytest.raises(UvgError):
            validate_name("../tools")

    def test_managed_environment_directory_uses_environment_override(self) -> None:
        assert get_venvs_dir() == self.managed_environments_directory

    def test_managed_environment_directory_uses_configured_home(self) -> None:
        configured_home_directory = Path(self.temporary_directory.name) / "custom-home"
        with patch.dict(
            "os.environ",
            {"UVG_HOME": str(configured_home_directory)},
            clear=True,
        ):
            assert get_venvs_dir() == configured_home_directory / "venvs"

    def test_list_managed_environment_names_returns_sorted_names(self) -> None:
        (self.managed_environments_directory / "zeta").mkdir(parents=True)
        (self.managed_environments_directory / "alpha").mkdir()

        assert list_names() == ["alpha", "zeta"]

    def test_read_python_version_reads_pyvenv_cfg_version_info(self) -> None:
        environment_path = self.managed_environments_directory / "tools"
        environment_path.mkdir(parents=True)
        (environment_path / "pyvenv.cfg").write_text(
            "version_info = 3.14.0rc3\n",
            encoding="utf-8",
        )

        assert read_python_version(environment_path) == "3.14.0rc3"

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
        with patch(
            "uvg.commands.env.list.typer.echo",
            side_effect=printed_lines.append,
        ):
            list_environments_command()

        assert printed_lines == ["alpha  3.12.11", "zeta   unknown"]

    @patch("uvg.core.environment.subprocess.run")
    def test_create_managed_environment_invokes_uv_with_expected_arguments(
        self,
        subprocess_run_mock: MagicMock,
    ) -> None:
        subprocess_run_mock.return_value = subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout="",
            stderr="",
        )

        environment_path = create("tools", "3.12")

        assert environment_path == self.managed_environments_directory / "tools"
        subprocess_run_mock.assert_called_once_with(
            [
                "uv",
                "venv",
                "--quiet",
                str(environment_path),
                "--seed",
                "--python",
                "3.12",
            ],
            capture_output=False,
            check=False,
            text=True,
        )

    def test_create_managed_environment_reports_missing_uv_executable(self) -> None:
        with (
            patch("uvg.core.environment.subprocess.run", side_effect=FileNotFoundError),
            pytest.raises(UvgError, match="The `uv` executable was not found"),
        ):
            create("tools")

        assert not (self.managed_environments_directory / "tools").exists()

    @patch("uvg.core.environment.subprocess.run")
    def test_create_reports_uv_failure(
        self,
        subprocess_run_mock: MagicMock,
    ) -> None:
        subprocess_run_mock.return_value = subprocess.CompletedProcess(
            args=[],
            returncode=1,
        )

        with pytest.raises(UvgError, match="Failed to create environment"):
            create("tools")

    @patch("uvg.commands.create.read_python_version", return_value="3.12.11")
    @patch("uvg.commands.create.create")
    def test_create_command_prints_stable_uvg_activation_instructions(
        self,
        create_mock: MagicMock,
        read_python_version_mock: MagicMock,
    ) -> None:
        environment_path = self.managed_environments_directory / "tools"
        create_mock.return_value = environment_path
        printed_lines: list[str] = []

        def capture_output(message: str = "") -> None:
            printed_lines.append(message)

        with patch("uvg.commands.create.typer.echo", side_effect=capture_output):
            create_environment_command("tools", "3.12")

        assert printed_lines == [
            "Created environment 'tools'",
            "Python: 3.12.11",
            f"Path: {environment_path}",
            "",
            "Activate with:",
            "  uvg activate tools",
        ]
        create_mock.assert_called_once_with("tools", "3.12")
        read_python_version_mock.assert_called_once_with(environment_path)

    @patch.dict("os.environ", {}, clear=True)
    def test_current_environment_name_returns_none_when_silent_without_active_environment(
        self,
    ) -> None:
        assert get_current_name(silent=True) is None

    def test_remove_managed_environment_refuses_active_environment(self) -> None:
        environment_path = self.managed_environments_directory / "tools"
        environment_path.mkdir(parents=True)

        with (
            patch.dict("os.environ", {"VIRTUAL_ENV": str(environment_path)}),
            pytest.raises(UvgError, match="currently active"),
        ):
            remove("tools")

    def test_remove_command_cancel_exits_successfully_without_removing(self) -> None:
        printed_lines: list[str] = []
        with (
            patch("uvg.commands.remove.typer.confirm", return_value=False),
            patch("uvg.commands.remove.typer.echo", side_effect=printed_lines.append),
            patch("uvg.commands.remove.remove") as remove_mock,
            pytest.raises(typer.Exit) as exit_context,
        ):
            remove_environment_command("tools")

        assert exit_context.value.exit_code == 0
        assert printed_lines == ["Aborted."]
        remove_mock.assert_not_called()
