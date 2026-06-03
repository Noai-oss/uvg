from __future__ import annotations

from importlib.metadata import distribution

import uvg
from uvg.__main__ import main as cli_main


def main() -> None:
    package = distribution("uvg")
    entry_points = package.entry_points

    assert package.metadata["Name"] == "uvg"
    assert uvg.__version__ == package.version
    assert any(
        entry_point.name == "uvg" and entry_point.value == "uvg.__main__:main"
        for entry_point in entry_points
    )
    assert cli_main(["--help"]) == 0


if __name__ == "__main__":
    main()
