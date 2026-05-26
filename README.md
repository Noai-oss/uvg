# uvg

A global Python virtual environment manager built on `uv`. Environments default to `~/.uvg/venvs`.

**`uv` for projects, `uvg` for environments.**

Set `UVG_HOME` to move the uvg home directory.

## Installation

```bash
# from pypi
uv tool install uvg
# local install
uv tool install .
# or
uv tool install git+https://github.com/Noai-oss/uvg
```

## Quick Start

```bash
# Initialize shell integration (pick one)
uvg init bash --profile ~/.bashrc
uvg init zsh --profile ~/.zshrc
uvg init pwsh --profile $PROFILE

# Create and activate an environment
uvg create myenv --python 3.12
uvg activate myenv

# Install packages
uv pip install ruff black
```

## Commands

| Command | Description | Example |
| --- | --- | --- |
| `uvg create <name>` | Create an environment | `uvg create data -p 3.11` |
| `uvg activate <name>` | Activate an environment | `uvg activate data` |
| `uvg remove <name>` | Remove an environment | `uvg remove data -y` |
| `uvg init <shell>` | Initialize shell integration for `bash`, `zsh`, or `pwsh` | `uvg init zsh -p ~/.zshrc` |
| `uvg env list` | List all environments | `uvg env list` |
| `uvg env current` | Show current environment | `uvg env current` |
| `uvg env dir` | Print the managed environments directory | `uvg env dir` |
