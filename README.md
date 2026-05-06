# uvg

A global Python virtual environment manager built on `uv`. Environments are stored in `~/.uvg/venvs`.

**`uv` for projects, `uvg` for environments.**

## Installation

```bash
uv tool install .
# or
uv tool install git+https://github.com/Noai-oss/uvg
```

## Quick Start

```bash
# Initialize shell integration (pick one)
uvg init bash --profile ~/.bashrc
uvg init zsh --profile ~/.zshrc
uvg init ps1 --profile $PROFILE

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
| `uvg list` | List all environments | `uvg list` |
| `uvg remove <name>` | Remove an environment | `uvg remove data -y` |
| `uvg current` | Show current environment | `uvg current` |
| `uvg info <name>` | Show environment info | `uvg info data` |
| `uvg path <name>` | Print environment path | `uvg path data` |
| `uvg init <shell>` | Initialize shell integration | `uvg init zsh -p ~/.zshrc` |
