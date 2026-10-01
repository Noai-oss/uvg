# uvg

A global Python virtual environment manager built on `uv`. Environments default to `~/.uvg/venvs`.

**`uv` for projects, `uvg` for environments.**

Set `UVG_HOME` to move the uvg home directory.

## Installation

```bash
# from PyPI
uv tool install uvg
# local install
uv tool install .
# or
uv tool install git+https://github.com/Noai-oss/uvg
```

## Quick Start

```bash
# Set up shell integration in an explicitly selected profile (pick one)
uvg setup bash --profile ~/.bashrc
uvg setup zsh --profile ~/.zshrc
uvg setup pwsh --profile $PROFILE

# Restart the shell, or reload the profile shown by setup

# Create and activate an environment
uvg create myenv --python 3.12
uvg activate myenv

# Install packages
uv pip install ruff black

# Leave the environment
uvg deactivate
```

## Commands

| Command | Description | Example |
| --- | --- | --- |
| `uvg create <name>` | Create an environment | `uvg create data -p 3.11` |
| `uvg activate <name>` | Activate an environment | `uvg activate data` |
| `uvg deactivate` | Deactivate the current environment | `uvg deactivate` |
| `uvg remove <name>` | Remove an environment | `uvg remove data -y` |
| `uvg setup <shell> --profile <path>` | Install, update, or remove shell integration | `uvg setup zsh -p ~/.zshrc` |
| `uvg shell hook <shell>` | Print the runtime hook to stdout | `uvg shell hook zsh` |
| `uvg shell activate <shell> <name>` | Print activation code to stdout | `uvg shell activate zsh data` |
| `uvg env list` | List all environments | `uvg env list` |
| `uvg env current` | Show current environment | `uvg env current` |
| `uvg env dir` | Print the managed environments directory | `uvg env dir` |

`setup` always requires both the shell and profile path. It never guesses which user
configuration file to modify. Preview or remove the managed block explicitly:

```bash
uvg setup zsh --profile ~/.zshrc --dry-run
uvg setup zsh --profile ~/.zshrc --remove
```

The `uvg shell ...` commands are low-level text interfaces: successful output contains
shell code only. They do not modify profile files.
