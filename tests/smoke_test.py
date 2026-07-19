from __future__ import annotations

import os
from importlib.metadata import distribution

import uvg
from uvg.__main__ import main as cli_main


def main() -> None:
    package = distribution("uvg")
    entry_points = package.entry_points
    expected_version = os.environ.get("EXPECTED_VERSION")

    assert package.metadata["Name"] == "uvg"
    assert uvg.__version__ == package.version
    if expected_version is not None:
        assert package.version == expected_version
    assert any(
        entry_point.name == "uvg" and entry_point.value == "uvg.__main__:main"
        for entry_point in entry_points
    )
    assert cli_main(["-h"]) == 0
    assert cli_main(["--help"]) == 0


if __name__ == "__main__":
    main()
