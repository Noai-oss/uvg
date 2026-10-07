# uvg

[English](README.md) | [简体中文](README_zh.md)

A global Python virtual environment manager built on `uv`.

**`uv` for projects, `uvg` for environments.**

## Installation

```bash
uv tool install uvg
# or install this checkout
uv tool install .
```

## Shell integration

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

Supported combinations are Linux and macOS with Bash or Zsh, and Windows with
PowerShell 7 or Git Bash. In Git Bash use the Bash loader. Windows PowerShell 5.1,
cmd.exe, Fish, and Linux PowerShell are outside the supported matrix.

## Quick start

```bash
uvg create myenv --python 3.12
uvg activate myenv
uv pip install ruff black
uvg deactivate
uvg remove myenv
```

uv is needed to create environments. Querying and activating existing environments
does not require uv on PATH.

## Commands

| Command | Description |
| --- | --- |
| `uvg create <name> [-p VERSION]` | Create an environment using uv venv --seed |
| `uvg activate <name>` | Source the standard script in the current shell |
| `uvg deactivate` | Call the current shell's standard deactivate function |
| `uvg remove <name> [-y]` | Remove an environment; confirm unless -y is given |
| `uvg env list` | List environments and their Python versions |
| `uvg env current` | Identify the managed directory referenced by VIRTUAL_ENV |
| `uvg env dir` | Print the environment root without creating it |
| `uvg shell hook <shell>` | Print the runtime hook |
| `uvg shell activate <shell> <name>` | Print code to source the standard script |

The low-level `shell` commands write code only to stdout on success. Errors go to
stderr with a nonzero status. The loader and hook never execute output from a
failed code-generation process.

## Environment directories

Environments are ordinary first-level directories under `~/.uvg/venvs`.
To move this root, set `UVG_HOME` to an absolute path; `~` is expanded. An unset
variable uses the default. An empty value or relative path is a configuration
error.

The path must not contain the platform's PATH separator (a semicolon on Windows,
a colon on Linux/macOS). Standard activation scripts cannot add such directories
to PATH as a single entry, so uvg rejects the configuration.

Names start with an ASCII letter or digit and then contain only ASCII letters,
digits, dots, underscores, or hyphens. Surrounding whitespace in a supplied name
is stripped. Environment symlinks and Windows junctions are not supported.

The directory is the source of truth: no registration file is required. Empty or
incomplete directories appear in the list with `unknown` when their Python
version cannot be read. Activation checks for the required standard script.
If a listing encounters an unsupported name or link, it still prints valid
environments, reports the invalid entries to stderr, and exits nonzero.

Failed creation leaves any files in place and reports their location. Inspect
them before removing the environment. Removal refuses the environment referenced
by this process's `VIRTUAL_ENV`; it does not track other terminals. A failed
recursive deletion can leave a partially removed directory.

## Activation and failure semantics

Activation, repeated activation, switching, and deactivation use the environment's
standard scripts. uvg does not maintain its own saved PATH, prompt, nesting stack,
or restoration state. `uvg deactivate` also works with an external standard venv
and does not need the uvg executable to remain on PATH.

A child shell may inherit `VIRTUAL_ENV` and PATH without inheriting a deactivate
function. Activating there still sources the standard script. Deactivation follows
that script's baseline, which may already include the parent environment; uvg
cannot reconstruct the parent's earlier PATH. `env current` reports the directory
reference, not the completeness of the shell's activation state.

Bash and Zsh preserve command status. The PowerShell wrapper guarantees numeric
`$LASTEXITCODE` only; do not use `$?`, `&&`, or `||` to determine its success.

```powershell
uvg activate myenv
$uvgStatus = $LASTEXITCODE
if ($uvgStatus -ne 0) {
    # Handle failure here.
}
```

## Migration

This is a breaking shell integration change:

- `uvg init` and `uvg setup` are removed. Manually replace old initialization
  commands or generated hook blocks with the loader above.
- The old `uvg activate --shell ...` code-generation interface is replaced by
  `uvg shell activate <shell> <name>`.
- Relative or empty `UVG_HOME` values must be replaced with an absolute path or
  unset to use the default.
- Paths containing the platform's PATH separator are rejected as well.
- Links and junctions in the environment directory are rejected. uvg does not
  move or delete their targets; reorganize these entries manually.
- Restart existing shells after replacing their initialization code.
