from __future__ import annotations

import os
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from .errors import UvgError


# ============================================================================
# Layout & Constants
# ============================================================================

UVG_HOME_DIR = Path.home() / ".uvg"
VENVS_DIR = UVG_HOME_DIR / "venvs"

NAME_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


# ============================================================================
# Types
# ============================================================================


@dataclass(frozen=True, slots=True)
class EnvironmentInfo:
    name: str
    path: Path
    python_executable: Path
    exists: bool


# ============================================================================
# Layout Functions
# ============================================================================


def ensure_layout() -> None:
    """Create the managed environments directory structure."""
    VENVS_DIR.mkdir(parents=True, exist_ok=True)


def build_path(environment_name: str) -> Path:
    """Build the path for a managed environment."""
    return VENVS_DIR / environment_name


def is_valid_path(path: str | Path) -> bool:
    """Check if a path is within the managed environments directory."""
    try:
        resolved_path = Path(path).resolve()
        managed_root_directory = VENVS_DIR.resolve()
        resolved_path.relative_to(managed_root_directory)
    except (OSError, ValueError):
        return False
    return True


def extract_name_from_path(path: str | Path) -> str | None:
    """Extract the environment name from a managed environment path."""
    try:
        resolved_path = Path(path).resolve()
        managed_root_directory = VENVS_DIR.resolve()
        relative_path = resolved_path.relative_to(managed_root_directory)
    except (OSError, ValueError):
        return None

    return relative_path.parts[0] if relative_path.parts else None


# ============================================================================
# Validation
# ============================================================================


def validate_name(environment_name: str) -> str:
    """Validate and normalize an environment name."""
    normalized_environment_name = environment_name.strip()

    if not normalized_environment_name:
        raise UvgError("Environment name cannot be empty.")

    if not NAME_PATTERN.fullmatch(normalized_environment_name):
        raise UvgError(
            "Environment name may only contain letters, numbers, dots, underscores, and hyphens."
        )

    return normalized_environment_name


# ============================================================================
# Runtime / Current Environment
# ============================================================================


def get_current_name(*, silent: bool = False) -> str | None:
    """Get the name of the currently active managed environment."""
    active_virtual_environment_path = os.environ.get("VIRTUAL_ENV")

    if not active_virtual_environment_path:
        if silent:
            return None
        raise UvgError("No active virtual environment.")

    if not is_valid_path(active_virtual_environment_path):
        if silent:
            return None
        raise UvgError(
            "An active virtual environment was found, but it is not managed by uvg.\n"
            f"Path: {active_virtual_environment_path}"
        )

    environment_name = extract_name_from_path(active_virtual_environment_path)
    if not environment_name:
        if silent:
            return None
        raise UvgError("Failed to determine current managed environment name.")

    return environment_name


# ============================================================================
# Registry Operations
# ============================================================================


def list_names() -> list[str]:
    """List all managed environment names."""
    if not VENVS_DIR.exists():
        return []

    environment_names = [
        candidate_path.name
        for candidate_path in VENVS_DIR.iterdir()
        if candidate_path.is_dir()
    ]
    return sorted(environment_names)


def resolve_path(environment_name: str) -> Path:
    """Resolve and validate an environment path."""
    normalized_environment_name = validate_name(environment_name)
    managed_environment_path = build_path(normalized_environment_name)

    if not managed_environment_path.exists():
        raise UvgError(f"Environment '{normalized_environment_name}' does not exist.")
    if not managed_environment_path.is_dir():
        raise UvgError(
            f"Path for environment '{normalized_environment_name}' exists but is not a directory."
        )

    return managed_environment_path


def remove(environment_name: str) -> None:
    """Remove a managed environment."""
    normalized_environment_name = validate_name(environment_name)
    managed_environment_path = resolve_path(normalized_environment_name)

    if get_current_name(silent=True) == normalized_environment_name:
        raise UvgError(
            f"Environment '{normalized_environment_name}' is currently active. "
            "Deactivate it before removing."
        )

    shutil.rmtree(managed_environment_path)


# ============================================================================
# UV Integration - Creation
# ============================================================================


def create(
    environment_name: str,
    python_version: str | None = None,
) -> Path:
    """Create a new managed environment using uv venv."""
    ensure_layout()

    normalized_environment_name = validate_name(environment_name)
    managed_environment_path = build_path(normalized_environment_name)

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


def read_python_version(environment_path: Path) -> str | None:
    """Read the Python version used by a managed environment."""
    pyvenv_cfg_path = environment_path / "pyvenv.cfg"
    if not pyvenv_cfg_path.exists():
        return None

    for line in pyvenv_cfg_path.read_text(encoding="utf-8").splitlines():
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        if key.strip() == "version_info":
            return value.strip()
    return None
