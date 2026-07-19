"""Transactional shell profile integration."""

from __future__ import annotations

import difflib
import os
import stat
import tempfile
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from uvg.core.errors import UvgError
from uvg.core.shell import ShellName, render_profile_loader

MARKER_PREFIX = "# >>> uvg shell integration: "
MARKER_SUFFIX = " >>>"
END_MARKER_PREFIX = "# <<< uvg shell integration: "
END_MARKER_SUFFIX = " <<<"


class ProfileAction(StrEnum):
    """A planned profile mutation."""

    initialize = "initialize"
    update = "update"
    remove = "remove"
    no_change = "no change"


@dataclass(frozen=True, slots=True)
class ProfileChange:
    """A complete, inspectable profile mutation plan."""

    path: Path
    action: ProfileAction
    before: str
    after: str
    newline: str
    line_endings_normalized: bool

    def render_diff(self) -> str:
        """Render this change as a unified diff."""
        if self.before == self.after:
            return ""
        return "".join(
            difflib.unified_diff(
                _diff_lines(self.before),
                _diff_lines(self.after),
                fromfile=str(self.path),
                tofile=str(self.path),
            ),
        )


def start_marker(shell_name: ShellName) -> str:
    """Return the opening marker for a shell block."""
    return f"{MARKER_PREFIX}{shell_name.value}{MARKER_SUFFIX}"


def end_marker(shell_name: ShellName) -> str:
    """Return the closing marker for a shell block."""
    return f"{END_MARKER_PREFIX}{shell_name.value}{END_MARKER_SUFFIX}"


def render_profile_block(shell_name: ShellName, newline: str = "\n") -> str:
    """Render the complete profile-managed block."""
    loader = render_profile_loader(shell_name).replace("\n", newline)
    lines = [
        start_marker(shell_name),
        "# This block is managed by `uvg setup`; edit outside the markers.",
        loader,
        end_marker(shell_name),
        "",
    ]
    return newline.join(lines)


def plan_profile_change(
    shell_name: ShellName,
    profile_path: Path,
    *,
    remove: bool = False,
) -> ProfileChange:
    """Plan an idempotent profile update without writing to disk."""
    path = profile_path.expanduser()
    before, contents, newline = _read_profile(path)
    line_endings_normalized = before != contents
    lines = contents.splitlines(keepends=True)
    marker_range = _find_marker_range(lines, shell_name, path)

    if marker_range is None:
        if remove:
            return ProfileChange(
                path=path,
                action=ProfileAction.no_change,
                before=before,
                after=before,
                newline=newline,
                line_endings_normalized=False,
            )
        block = render_profile_block(shell_name, newline)
        after = _append_block(contents, block, newline)
        return ProfileChange(
            path=path,
            action=ProfileAction.initialize,
            before=before,
            after=after,
            newline=newline,
            line_endings_normalized=line_endings_normalized,
        )

    start_index, end_index = marker_range
    if remove:
        after = "".join([*lines[:start_index], *lines[end_index + 1 :]])
        return ProfileChange(
            path=path,
            action=ProfileAction.remove,
            before=before,
            after=after,
            newline=newline,
            line_endings_normalized=line_endings_normalized,
        )

    block = render_profile_block(shell_name, newline)
    after = "".join([*lines[:start_index], block, *lines[end_index + 1 :]])
    action = ProfileAction.no_change if after == before else ProfileAction.update
    return ProfileChange(
        path=path,
        action=action,
        before=before,
        after=after,
        newline=newline,
        line_endings_normalized=line_endings_normalized,
    )


def apply_profile_change(change: ProfileChange) -> None:
    """Apply a planned profile mutation atomically."""
    if change.action is ProfileAction.no_change:
        return
    temporary_path: Path | None = None
    try:
        write_path = change.path.resolve() if change.path.is_symlink() else change.path
        write_path.parent.mkdir(parents=True, exist_ok=True)
        payload = change.after.encode("utf-8")

        existing_mode: int | None = None
        if write_path.exists():
            existing_mode = stat.S_IMODE(write_path.stat().st_mode)

        with tempfile.NamedTemporaryFile(
            dir=write_path.parent,
            prefix=f".{write_path.name}.",
            suffix=".tmp",
            delete=False,
        ) as temporary_file:
            temporary_path = Path(temporary_file.name)
            temporary_file.write(payload)
            temporary_file.flush()
            os.fsync(temporary_file.fileno())

        if existing_mode is not None:
            temporary_path.chmod(existing_mode)
        temporary_path.replace(write_path)
    except UvgError:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)
        raise
    except OSError as exc:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)
        raise UvgError(f"Could not update profile '{change.path}': {exc}") from exc


def _read_profile(path: Path) -> tuple[str, str, str]:
    try:
        if not path.exists():
            return "", "", os.linesep
        if not path.is_file():
            raise UvgError(f"Profile path is not a file: {path}")
        payload = path.read_bytes()
    except OSError as exc:
        raise UvgError(f"Could not read profile '{path}': {exc}") from exc

    try:
        contents = payload.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise UvgError(f"Profile is not valid UTF-8: {path}") from exc

    # NOTE: This intentionally mirrors the VS Code Python Environments profile
    # editor: any CRLF selects CRLF and the edited file is normalized as a whole.
    # Reference:
    # https://github.com/microsoft/vscode-python-environments/blob/main/src/features/terminal/shells/common/editUtils.ts
    if "\r\n" in contents:
        newline = "\r\n"
    elif "\n" in contents:
        newline = "\n"
    else:
        newline = os.linesep

    normalized_contents = contents.replace("\r\n", "\n")
    if newline == "\r\n":
        normalized_contents = normalized_contents.replace("\n", "\r\n")
    return contents, normalized_contents, newline


def _diff_lines(contents: str) -> list[str]:
    """Render profile text safely in a platform-independent unified diff."""
    display_contents = contents.replace("\r\n", "\n").replace("\r", r"\r")
    return display_contents.splitlines(keepends=True)


def _find_marker_range(
    lines: list[str],
    shell_name: ShellName,
    path: Path,
) -> tuple[int, int] | None:
    starts = [
        (index, line.rstrip("\r\n"))
        for index, line in enumerate(lines)
        if line.rstrip("\r\n").startswith(MARKER_PREFIX)
    ]
    ends = [
        (index, line.rstrip("\r\n"))
        for index, line in enumerate(lines)
        if line.rstrip("\r\n").startswith(END_MARKER_PREFIX)
    ]
    if not starts and not ends:
        return None
    if len(starts) != 1 or len(ends) != 1:
        raise UvgError(f"Profile contains malformed or duplicate uvg markers: {path}")

    start_index, actual_start = starts[0]
    end_index, actual_end = ends[0]
    if (
        actual_start != start_marker(shell_name)
        or actual_end != end_marker(shell_name)
        or start_index >= end_index
    ):
        raise UvgError(
            f"Profile contains uvg integration for another shell or malformed markers: {path}",
        )
    return start_index, end_index


def _append_block(contents: str, block: str, newline: str) -> str:
    if not contents:
        return block
    if contents.endswith(newline * 2):
        return contents + block
    if contents.endswith(newline):
        return contents + newline + block
    return contents + newline + newline + block
