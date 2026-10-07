# uvg

[English](README.md) | [简体中文](README_zh.md)

基于 `uv` 的全局 Python 虚拟环境管理工具。

**用 `uv` 管理项目，用 `uvg` 管理环境。**

## 安装

```bash
uv tool install uvg
```

## Shell 集成

正式支持 Linux 和 macOS 上的 Bash、Zsh，以及 Windows 上的 PowerShell 7、Git Bash。
Git Bash 使用下方的 Bash 加载片段。

将下方对应的加载片段添加到 shell 配置文件，然后重启 shell 或重新加载该文件。
请自行选择配置文件，例如 `~/.bashrc`、`~/.zshrc` 或 PowerShell 的 `$PROFILE`。
uvg 不会修改你的配置文件。

每个新启动的 shell 都会从当前安装的 uvg 加载 hook。升级 uvg 后，也需要重启已有的
shell，或重新加载配置文件。

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

在 PowerShell 脚本中，调用 uvg 后请检查 `$LASTEXITCODE`，不要用 `$?`、`&&` 或 `||`
判断操作是否成功，详见[退出状态](docs/reference_zh.md#退出状态)。

## 快速开始

```bash
uvg create myenv --python 3.12
uvg activate myenv
uv pip install ruff black
uvg deactivate
uvg remove myenv
```

## 命令

| 命令 | 说明 |
| --- | --- |
| `uvg create <name> [-p VERSION]` | 创建命名环境 |
| `uvg activate <name>` | 在当前 shell 中激活环境 |
| `uvg deactivate` | 退出当前环境 |
| `uvg remove <name> [-y]` | 删除环境；未指定 -y 时会请求确认 |
| `uvg env list` | 列出环境及其 Python 版本 |
| `uvg env current` | 显示当前受管理环境的名称 |
| `uvg env dir` | 输出环境目录 |

运行 `uvg <command> --help` 查看选项。

## 配置与参考

环境默认保存在 `~/.uvg/venvs` 下。将 `UVG_HOME` 设置为绝对路径，可改用
`UVG_HOME/venvs` 存放环境，详见[目录配置](docs/reference_zh.md#环境目录)。

目录规则、shell 行为和脚本接口见[使用参考](docs/reference_zh.md)。
版本历史见[更新日志](CHANGELOG.md)。
