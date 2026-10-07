# uvg reference

[English](reference.md) | [简体中文](reference_zh.md) · [Back to README](../README.md)

This reference covers directory configuration, shell behavior, and scripting.
For installation and shell setup, start with the [README](../README.md#shell-integration).

## Environment directories

Environments are ordinary first-level directories under `~/.uvg/venvs`.
Set `UVG_HOME` to change their location to `UVG_HOME/venvs`.

- `UVG_HOME` must be an absolute path after expanding `~`. Only an unset variable
  uses the default; an empty value or relative path is a configuration error.
- The path must not contain the platform's PATH separator: a semicolon on Windows
  or a colon on Linux/macOS. Standard activation scripts cannot add such paths to
  PATH as a single entry.
- Names start with an ASCII letter or digit and then contain only ASCII letters,
  digits, dots, underscores, or hyphens. Surrounding whitespace in a supplied name
  is stripped.
- Environment symlinks and Windows junctions are not supported.

No registration file is required. Empty or incomplete directories appear in
`uvg env list`, with `unknown` when their Python version cannot be read. Activation
checks for the required standard script. If a listing encounters an unsupported
name or link, it still prints valid environments, reports invalid entries to
stderr, and exits nonzero.

`uvg env dir` prints the configured directory without creating it. Listing a
missing directory produces an empty result; an unreadable directory is an error.

## Creating and removing environments

Creation invokes `uv venv --seed`, with `--python` when a version is supplied.
uv is needed to create environments; querying and activating existing environments
does not require uv on PATH.

Failed creation leaves any files in place and reports their location. Inspect
them before removing the environment. `uvg remove` asks for confirmation unless
`-y` is given; cancelling leaves the environment in place and exits successfully.

Removal refuses the environment referenced by this process's `VIRTUAL_ENV`; it
does not track other terminals. A failed recursive deletion can leave a partially
removed directory.

## Shell behavior

The supported platforms and shell loaders are listed in the
[README](../README.md#shell-integration).

Activation, repeated activation, switching, and deactivation use the environment's
standard scripts. `uvg deactivate` also works with an external standard venv and
does not need the uvg executable to remain on PATH. Without a deactivate function
in the current shell, it reports an error.

A child shell may inherit `VIRTUAL_ENV` and PATH without inheriting a deactivate
function. Activating there still sources the standard script. Deactivation follows
that script's baseline, which may already include the parent environment; uvg
cannot reconstruct the parent's earlier PATH or maintain a stack of environments.
`uvg env current` identifies the ordinary first-level environment directory
referenced by `VIRTUAL_ENV`; it does not verify the shell's full activation state.

### Exit status

Bash and Zsh preserve command status. The PowerShell wrapper guarantees numeric
`$LASTEXITCODE` only; do not use `$?`, `&&`, or `||` to determine its success.

```powershell
uvg activate myenv
$uvgStatus = $LASTEXITCODE
if ($uvgStatus -ne 0) {
    # Handle failure here.
}
```

### Shell-code interfaces

These commands print code for the caller to execute; they do not activate an
environment in the parent shell themselves.

| Command | Output |
| --- | --- |
| `uvg shell hook <shell>` | The runtime shell function |
| `uvg shell activate <shell> <name>` | Code to source the environment's standard activation script |

`<shell>` is `bash`, `zsh`, or `pwsh`. On success, stdout contains only UTF-8 code
with LF line endings. Errors go to stderr with a nonzero status. The loader and
hook never execute output from a failed code-generation process. If the standard
script itself fails, the failure is reported; partial shell changes are not rolled
back.

## Installing a checkout

To install from a local copy of this repository, run this from its root:

```bash
uv tool install .
```
