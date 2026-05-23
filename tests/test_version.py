from __future__ import annotations

from importlib.metadata import version

import uvg


def test_package_version_comes_from_installed_metadata() -> None:
    assert uvg.__version__ == version("uvg")
