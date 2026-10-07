"""Filesystem and uv operations for named environments."""

from __future__ import annotations

import os
import re
import shutil
import stat
import subprocess
from pathlib import Path

from .errors import UvgError

NAME_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


def get_venvs_dir() -> Path:
    """Read the configured absolute environment root without creating it."""
    configured_home = os.environ.get("UVG_HOME")
    if configured_home is None:
        home = Path.home() / ".uvg"
    else:
        try:
            home = Path(configured_home).expanduser()
        except RuntimeError as exc:
            raise UvgError(f"Invalid UVG_HOME: {exc}") from exc
        if not configured_home or not home.is_absolute():
            raise UvgError("UVG_HOME must be a nonempty absolute path (after expanding ~).")
    if os.pathsep in str(home):
        raise UvgError(f"UVG_HOME cannot contain the PATH separator {os.pathsep!r}: {home}")
    return home / "venvs"


def validate_name(name: str) -> str:
    """Normalize and validate a name supplied by the user."""
    name = name.strip()
    if not name:
        raise UvgError("Environment name cannot be empty.")
    if not NAME_PATTERN.fullmatch(name):
        raise UvgError(
            "Environment name must start with a letter or number and contain only "
            "ASCII letters, numbers, dots, underscores, and hyphens.",
        )
    return name


def _is_regular_directory(path: Path) -> bool:
    """Inspect an entry without following environment links."""
    mode = path.lstat().st_mode
    if stat.S_ISLNK(mode) or path.is_junction():
        raise UvgError(f"Environment links and junctions are not supported: {path}")
    return stat.S_ISDIR(mode)


def resolve_path(root: Path, name: str) -> Path:
    """Validate a name and locate its existing ordinary directory."""
    path = root / validate_name(name)
    try:
        is_directory = _is_regular_directory(path)
    except FileNotFoundError as exc:
        raise UvgError(
            f"Environment '{path.name}' does not exist.\nList environments with:\n  uvg env list",
        ) from exc
    except OSError as exc:
        raise UvgError(f"Could not inspect environment '{path}': {exc}") from exc
    if not is_directory:
        raise UvgError(f"Environment path exists but is not a directory: {path}")
    return path


def list_environments(root: Path) -> tuple[list[Path], list[str]]:
    """Discover ordinary directories and report unsupported entries separately."""
    try:
        entries = sorted(root.iterdir(), key=lambda path: path.name)
    except FileNotFoundError:
        return [], []
    except OSError as exc:
        raise UvgError(f"Could not list environments in '{root}': {exc}") from exc

    environments: list[Path] = []
    errors: list[str] = []
    for path in entries:
        try:
            if not _is_regular_directory(path):
                continue
            if not NAME_PATTERN.fullmatch(path.name):
                raise UvgError(f"Unsupported environment directory name: {path}")
        except (OSError, UvgError) as exc:
            errors.append(str(exc))
        else:
            environments.append(path)
    return environments, errors


def get_current_name(root: Path, active_environment: str | None) -> str:
    """Identify an ordinary first-level environment referenced by VIRTUAL_ENV."""
    if not active_environment:
        raise UvgError("No active virtual environment.")
    active_path = Path(active_environment)
    try:
        is_directory = _is_regular_directory(active_path)
        resolved = active_path.resolve()
        managed_root = root.resolve()
    except OSError as exc:
        raise UvgError(f"Could not inspect active environment '{active_path}': {exc}") from exc
    if not is_directory or resolved.parent != managed_root:
        raise UvgError(
            f"The active virtual environment is not managed by uvg.\nPath: {active_path}",
        )
    if not NAME_PATTERN.fullmatch(resolved.name):
        raise UvgError(f"Unsupported environment directory name: {resolved}")
    return resolved.name


def remove(path: Path, active_environment: str | None) -> None:
    """Delete a located environment, refusing the current process's active one."""
    try:
        if active_environment:
            try:
                is_active = Path(active_environment).samefile(path)
            except FileNotFoundError:
                is_active = False
            if is_active:
                raise UvgError(
                    f"Environment '{path.name}' is currently active. "
                    "Deactivate it before removing.",
                )
        shutil.rmtree(path)
    except OSError as exc:
        raise UvgError(f"Could not remove environment '{path}': {exc}") from exc


def create(root: Path, name: str, python_version: str | None = None) -> Path:
    """Create an environment with uv, preserving files left by a failed call."""
    path = root / validate_name(name)
    try:
        try:
            _is_regular_directory(path)
        except FileNotFoundError:
            pass
        else:
            raise UvgError(f"Environment '{path.name}' already exists: {path}")
        root.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise UvgError(f"Could not prepare environment '{path}': {exc}") from exc

    command = ["uv", "venv", "--quiet", str(path), "--seed"]
    if python_version:
        command.extend(["--python", python_version])
    try:
        result = subprocess.run(command, check=False)  # noqa: S603
    except FileNotFoundError as exc:
        raise UvgError("The uv executable was not found. Install it and add it to PATH.") from exc
    except OSError as exc:
        raise UvgError(f"Could not run uv to create '{path}': {exc}") from exc
    if result.returncode != 0:
        raise UvgError(
            f"Failed to create environment '{path.name}'.\n"
            f"Inspect any files left at: {path}\n"
            "No automatic cleanup was performed.",
        )
    return path


def read_python_version(path: Path) -> str | None:
    """Read optional display metadata without maintaining a second version record."""
    try:
        contents = (path / "pyvenv.cfg").read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return None
    for line in contents.splitlines():
        key, separator, value = line.partition("=")
        if separator and key.strip() == "version_info":
            return value.strip() or None
    return None
