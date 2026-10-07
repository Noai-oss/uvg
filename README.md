# uvg

[English](README.md) | [简体中文](README_zh.md)

A global Python virtual environment manager built on `uv`.

**`uv` for projects, `uvg` for environments.**

## Installation

```bash
uv tool install uvg
```

## Shell integration

Supported: Linux and macOS with Bash or Zsh; Windows with PowerShell 7 or Git Bash.
For Git Bash, use the Bash loader below.

Add the matching loader below to your shell profile, then restart the shell or
reload that file. Choose the profile yourself (for example, `~/.bashrc`,
`~/.zshrc`, or PowerShell's `$PROFILE`). uvg never edits your profile.

Each new shell loads the hook from the currently installed uvg. After upgrading
uvg, restart or reload existing shells as well.

### Bash

<!-- uvg-loader:bash -->
```bash
if command -v uvg >/dev/null 2>&1; then
    if _uvg_hook="$(command uvg shell hook bash)"; then
        eval "$_uvg_hook"
    fi
fi
unset _uvg_hook
```

### Zsh

<!-- uvg-loader:zsh -->
```zsh
if command -v uvg >/dev/null 2>&1; then
    if _uvg_hook="$(command uvg shell hook zsh)"; then
        eval "$_uvg_hook"
    fi
fi
unset _uvg_hook
```

### PowerShell 7

<!-- uvg-loader:pwsh -->
```powershell
& {
    $uvgCommand = Get-Command uvg -CommandType Application -TotalCount 1 -ErrorAction SilentlyContinue
    if ($null -eq $uvgCommand) { return }
    $uvgHook = & $uvgCommand.Source shell hook pwsh
    if ($LASTEXITCODE -eq 0) {
        Invoke-Expression ($uvgHook -join "`n")
    }
}
```

In PowerShell scripts, check `$LASTEXITCODE` after calling uvg. Do not use `$?`,
`&&`, or `||` to decide whether it succeeded; see [exit status](docs/reference.md#exit-status).

## Quick start

```bash
uvg create myenv --python 3.12
uvg activate myenv
uv pip install ruff black
uvg deactivate
uvg remove myenv
```

## Commands

| Command | Description |
| --- | --- |
| `uvg create <name> [-p VERSION]` | Create a named environment |
| `uvg activate <name>` | Activate an environment in the current shell |
| `uvg deactivate` | Deactivate the current environment |
| `uvg remove <name> [-y]` | Remove an environment; confirm unless -y is given |
| `uvg env list` | List environments and their Python versions |
| `uvg env current` | Show the current managed environment's name |
| `uvg env dir` | Print the environment directory |

Run `uvg <command> --help` for options.

## Configuration and reference

Environments are stored in `~/.uvg/venvs` by default. Set `UVG_HOME` to an absolute
path to use `UVG_HOME/venvs` instead; see [directory configuration](docs/reference.md#environment-directories).

See the [reference](docs/reference.md) for directory rules, shell behavior, and
scripting interfaces, and the [changelog](CHANGELOG.md) for release history.
