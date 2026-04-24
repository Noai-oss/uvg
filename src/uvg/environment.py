from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from .errors import UvgError


# ============================================================================
# Layout & Constants
# ============================================================================

UVG_HOME_DIRECTORY = Path.home() / ".uvg"
MANAGED_ENVIRONMENTS_DIRECTORY = UVG_HOME_DIRECTORY / "venvs"

MANAGED_ENVIRONMENT_NAME_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


# ============================================================================
# Types
# ============================================================================


@dataclass(frozen=True, slots=True)
class ManagedEnvironmentInfo:
    name: str
    path: Path
    python_executable: Path
    exists: bool


# ============================================================================
# Layout Functions
# ============================================================================


def ensure_managed_environment_layout_exists() -> None:
    """Create the managed environments directory structure."""
    MANAGED_ENVIRONMENTS_DIRECTORY.mkdir(parents=True, exist_ok=True)


def build_managed_environment_path(environment_name: str) -> Path:
    """Build the path for a managed environment."""
    return MANAGED_ENVIRONMENTS_DIRECTORY / environment_name


def is_managed_environment_path(path: str | Path) -> bool:
    """Check if a path is within the managed environments directory."""
    try:
        resolved_path = Path(path).resolve()
        managed_root_directory = MANAGED_ENVIRONMENTS_DIRECTORY.resolve()
        resolved_path.relative_to(managed_root_directory)
    except (OSError, ValueError):
        return False
    return True


def get_managed_environment_name_from_path(path: str | Path) -> str | None:
    """Extract the environment name from a managed environment path."""
    try:
        resolved_path = Path(path).resolve()
        managed_root_directory = MANAGED_ENVIRONMENTS_DIRECTORY.resolve()
        relative_path = resolved_path.relative_to(managed_root_directory)
    except (OSError, ValueError):
        return None

    return relative_path.parts[0] if relative_path.parts else None


# ============================================================================
# Validation
# ============================================================================


def validate_managed_environment_name(environment_name: str) -> str:
    """Validate and normalize an environment name."""
    normalized_environment_name = environment_name.strip()

    if not normalized_environment_name:
        raise UvgError("Environment name cannot be empty.")

    if not MANAGED_ENVIRONMENT_NAME_PATTERN.fullmatch(normalized_environment_name):
        raise UvgError(
            "Environment name may only contain letters, numbers, dots, underscores, and hyphens."
        )

    return normalized_environment_name


# ============================================================================
# Runtime / Current Environment
# ============================================================================


def current_environment_name(*, silent: bool = False) -> str | None:
    """Get the name of the currently active managed environment."""
    active_virtual_environment_path = os.environ.get("VIRTUAL_ENV")

    if not active_virtual_environment_path:
        if silent:
            return None
        raise UvgError("No active virtual environment.")

    if not is_managed_environment_path(active_virtual_environment_path):
        if silent:
            return None
        raise UvgError(
            "An active virtual environment was found, but it is not managed by uvg.\n"
            f"Path: {active_virtual_environment_path}"
        )

    environment_name = get_managed_environment_name_from_path(
        active_virtual_environment_path
    )
    if not environment_name:
        if silent:
            return None
        raise UvgError("Failed to determine current managed environment name.")

    return environment_name


# ============================================================================
# Registry Operations
# ============================================================================


def list_managed_environment_names() -> list[str]:
    """List all managed environment names."""
    if not MANAGED_ENVIRONMENTS_DIRECTORY.exists():
        return []

    environment_names = [
        candidate_path.name
        for candidate_path in MANAGED_ENVIRONMENTS_DIRECTORY.iterdir()
        if candidate_path.is_dir()
    ]
    return sorted(environment_names)


def resolve_managed_environment_path(environment_name: str) -> Path:
    """Resolve and validate an environment path."""
    normalized_environment_name = validate_managed_environment_name(environment_name)
    managed_environment_path = build_managed_environment_path(
        normalized_environment_name
    )

    if not managed_environment_path.exists():
        raise UvgError(f"Environment '{normalized_environment_name}' does not exist.")
    if not managed_environment_path.is_dir():
        raise UvgError(
            f"Path for environment '{normalized_environment_name}' exists but is not a directory."
        )

    return managed_environment_path


def remove_managed_environment(environment_name: str) -> None:
    """Remove a managed environment."""
    normalized_environment_name = validate_managed_environment_name(environment_name)
    managed_environment_path = resolve_managed_environment_path(
        normalized_environment_name
    )

    if current_environment_name(silent=True) == normalized_environment_name:
        raise UvgError(
            f"Environment '{normalized_environment_name}' is currently active. "
            "Deactivate it before removing."
        )

    shutil.rmtree(managed_environment_path)


def get_managed_environment_info(
    environment_name: str,
    *,
    raise_if_missing: bool = True,  # [TODO] 这个参数是有待确认
) -> ManagedEnvironmentInfo:
    """Get information about a managed environment."""
    normalized_environment_name = validate_managed_environment_name(environment_name)
    managed_environment_path = build_managed_environment_path(
        normalized_environment_name
    )
    environment_exists = managed_environment_path.exists()

    if raise_if_missing and not environment_exists:
        raise UvgError(f"Environment '{normalized_environment_name}' does not exist.")

    python_executable_path = build_python_executable_path_for_environment(
        managed_environment_path
    )

    return ManagedEnvironmentInfo(
        name=managed_environment_path.name,
        path=managed_environment_path,
        python_executable=python_executable_path,
        exists=environment_exists,
    )


def build_python_executable_path_for_environment(environment_path: Path) -> Path:
    """Build the path to the Python executable in an environment."""
    if sys.platform.startswith("win"):
        return environment_path / "Scripts" / "python.exe"
    return environment_path / "bin" / "python"


# ============================================================================
# UV Integration - Creation
# ============================================================================


def create_managed_environment(
    environment_name: str,
    python_version: str | None = None,
) -> Path:
    """Create a new managed environment using uv venv."""
    ensure_managed_environment_layout_exists()

    normalized_environment_name = validate_managed_environment_name(environment_name)
    managed_environment_path = build_managed_environment_path(
        normalized_environment_name
    )

    if managed_environment_path.exists():
        raise UvgError(f"Environment '{normalized_environment_name}' already exists.")

    create_environment_command = ["uv", "venv", str(managed_environment_path), "--seed"]
    if python_version:
        create_environment_command.extend(["--python", python_version])

    try:
        completed_process = subprocess.run(
            create_environment_command,
            capture_output=True,
            check=False,
            text=True,
        )
    except FileNotFoundError as exc:
        raise UvgError(
            "The `uv` executable was not found. Install `uv` and ensure it is available on PATH."
        ) from exc

    if completed_process.returncode != 0:
        standard_error_output = (completed_process.stderr or "").strip()
        raise UvgError(
            f"Failed to create environment '{normalized_environment_name}'."
            + (f"\n{standard_error_output}" if standard_error_output else "")
        )

    return managed_environment_path
