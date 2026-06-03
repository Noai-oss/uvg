from __future__ import annotations

from importlib.metadata import version
from pathlib import Path

import uvg


def test_package_version_comes_from_installed_metadata() -> None:
    if not Path(uvg.__file__).with_name("_version.py").exists():
        assert uvg.__version__ == "0.0.0"
        return

    assert uvg.__version__ == version("uvg")
