from __future__ import annotations

import os
import subprocess
from pathlib import Path
from unittest.mock import Mock

import pytest
from typer.testing import CliRunner

from uvg.__main__ import main
from uvg.cli import app
from uvg.core import environment
from uvg.core.errors import UvgError

runner = CliRunner()


@pytest.fixture
def root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("UVG_HOME", str(tmp_path))
    monkeypatch.delenv("VIRTUAL_ENV", raising=False)
    path = tmp_path / "venvs"
    path.mkdir()
    return path


@pytest.mark.parametrize("value", ["", ".", "relative/path"])
def test_invalid_home_does_not_create_files(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    value: str,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("UVG_HOME", value)
    assert main(["create", "tools"]) == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "absolute path" in captured.err
    assert list(tmp_path.iterdir()) == []


def test_home_default_and_tilde_expansion(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("UVG_HOME", raising=False)
    assert environment.get_venvs_dir() == Path.home() / ".uvg" / "venvs"
    monkeypatch.setenv("UVG_HOME", "~/custom-uvg")
    assert environment.get_venvs_dir() == Path.home() / "custom-uvg" / "venvs"
    monkeypatch.setenv("UVG_HOME", str(tmp_path))
    assert environment.get_venvs_dir() == tmp_path / "venvs"
    assert not (tmp_path / "venvs").exists()


def test_home_rejects_path_separator(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("UVG_HOME", str(tmp_path / f"bad{os.pathsep}home"))
    with pytest.raises(UvgError, match="PATH separator"):
        environment.get_venvs_dir()
    assert list(tmp_path.iterdir()) == []


def test_invalid_name_has_no_creation_side_effects(tmp_path: Path) -> None:
    root = tmp_path / "missing" / "venvs"
    with pytest.raises(UvgError, match="Environment name"):
        environment.create(root, "../outside")
    assert list(tmp_path.iterdir()) == []


def test_list_reports_invalid_entries_with_valid_results(root: Path) -> None:
    (root / "tools").mkdir()
    (root / "bad name").mkdir()
    (root / "plain-file").write_text("ignored", encoding="utf-8")
    result = runner.invoke(app, ["env", "list"])
    assert result.exit_code == 1
    assert result.stdout == "tools  unknown\n"
    assert "bad name" in result.stderr
    assert "plain-file" not in result.stderr


def test_unreadable_root_is_not_an_empty_list(root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(Path, "iterdir", Mock(side_effect=PermissionError("denied")))
    with pytest.raises(UvgError, match="Could not list environments"):
        environment.list_environments(root)


@pytest.mark.parametrize("relative", [".", "tools/nested", "../external"])
def test_current_requires_an_exact_first_level_environment(root: Path, relative: str) -> None:
    active = root / relative
    active.mkdir(parents=True, exist_ok=True)
    with pytest.raises(UvgError, match="not managed by uvg"):
        environment.get_current_name(root, str(active))


def test_current_reports_an_ordinary_directory_without_activation_state(root: Path) -> None:
    path = root / "tools"
    path.mkdir()
    assert environment.get_current_name(root, str(path)) == "tools"


@pytest.mark.parametrize("contents", [b"\xff", b"version_info =\n", b"not a config"])
def test_unavailable_version_is_optional(root: Path, contents: bytes) -> None:
    path = root / "tools"
    path.mkdir()
    (path / "pyvenv.cfg").write_bytes(contents)
    assert environment.read_python_version(path) is None


def test_failed_creation_preserves_files(root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    def fail_create(command: list[str], *, check: bool) -> subprocess.CompletedProcess[str]:
        assert not check
        path = Path(command[3])
        path.mkdir()
        (path / "partial").write_text("keep", encoding="utf-8")
        return subprocess.CompletedProcess(command, 1)

    monkeypatch.setattr(environment.subprocess, "run", fail_create)
    with pytest.raises(UvgError, match="Inspect any files left at"):
        environment.create(root, "tools")
    assert (root / "tools" / "partial").read_text(encoding="utf-8") == "keep"


def test_remove_handles_stale_active_path_and_reports_io_failure(
    root: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = root / "tools"
    path.mkdir()
    environment.remove(path, str(root / "missing"))
    assert not path.exists()
    path.mkdir()
    monkeypatch.setattr(environment.shutil, "rmtree", Mock(side_effect=PermissionError("in use")))
    with pytest.raises(UvgError, match=r"Could not remove environment.*in use"):
        environment.remove(path, None)


def _check_link_rejected(root: Path, target: Path) -> None:
    result = runner.invoke(app, ["env", "list"])
    assert result.exit_code == 1
    assert "links and junctions are not supported" in result.stderr
    for command in (
        ["remove", "linked", "-y"],
        ["shell", "activate", "bash", "linked"],
        ["create", "linked"],
    ):
        result = runner.invoke(app, command)
        assert result.exit_code == 1
        assert "links and junctions are not supported" in str(result.exception)
        assert result.stdout == ""
    with pytest.raises(UvgError, match="links and junctions are not supported"):
        environment.get_current_name(root, str(root / "linked"))
    assert (target / "keep").read_text(encoding="utf-8") == "safe"


@pytest.mark.skipif(os.name == "nt", reason="POSIX symlink test; Windows uses a real junction")
@pytest.mark.parametrize("dangling", [False, True])
def test_environment_symlinks_are_rejected(root: Path, *, dangling: bool) -> None:
    target = root.parent / "outside"
    target.mkdir()
    (target / "keep").write_text("safe", encoding="utf-8")
    (root / "linked").symlink_to(
        target / "missing" if dangling else target, target_is_directory=True
    )
    _check_link_rejected(root, target)


@pytest.mark.skipif(os.name != "nt", reason="Windows junction test")
def test_environment_junctions_are_rejected(root: Path) -> None:
    target = root.parent / "outside"
    target.mkdir()
    (target / "keep").write_text("safe", encoding="utf-8")
    subprocess.run(  # noqa: S603
        [os.environ["COMSPEC"], "/d", "/c", "mklink", "/J", str(root / "linked"), str(target)],
        check=True,
        capture_output=True,
    )
    assert (root / "linked").is_junction()
    _check_link_rejected(root, target)


def test_missing_activation_script_has_no_stdout(
    root: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    (root / "broken").mkdir()
    assert main(["shell", "activate", "bash", "broken"]) == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "Missing activation script" in captured.err
