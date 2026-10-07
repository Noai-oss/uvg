# uvg

[English](README.md) | [简体中文](README_zh.md)

基于 `uv` 的全局 Python 虚拟环境管理工具。

**用 `uv` 管理项目，用 `uvg` 管理环境。**

## 安装

```bash
uv tool install uvg
# 或安装当前仓库中的代码
uv tool install .
```

## Shell 集成

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

正式支持 Linux 和 macOS 上的 Bash、Zsh，以及 Windows 上的 PowerShell 7、Git Bash。
Git Bash 使用上面的 Bash 加载片段。Windows PowerShell 5.1、cmd.exe、Fish 和
Linux 上的 PowerShell 不在正式支持范围内。

## 快速开始

```bash
uvg create myenv --python 3.12
uvg activate myenv
uv pip install ruff black
uvg deactivate
uvg remove myenv
```

创建环境需要 uv。查询和激活已有环境不要求 PATH 中存在 uv。

## 命令

| 命令 | 说明 |
| --- | --- |
| `uvg create <name> [-p VERSION]` | 使用 uv venv --seed 创建环境 |
| `uvg activate <name>` | 在当前 shell 中加载标准激活脚本 |
| `uvg deactivate` | 调用当前 shell 的标准 deactivate 函数 |
| `uvg remove <name> [-y]` | 删除环境；未指定 -y 时会请求确认 |
| `uvg env list` | 列出环境及其 Python 版本 |
| `uvg env current` | 识别 VIRTUAL_ENV 指向的受管理环境目录 |
| `uvg env dir` | 输出环境根目录，不创建目录 |
| `uvg shell hook <shell>` | 输出运行时 hook |
| `uvg shell activate <shell> <name>` | 输出用于加载标准激活脚本的代码 |

底层 `shell` 命令成功时仅向 stdout 输出代码；失败时向 stderr 输出诊断，并返回非零状态。
加载片段和 hook 都不会执行代码生成进程失败时输出的内容。

## 环境目录

环境是 `~/.uvg/venvs` 下的普通一级目录。可以通过 `UVG_HOME` 更改存储位置，环境将保存在
`UVG_HOME/venvs` 下。`UVG_HOME` 必须是绝对路径，允许展开 `~`；未设置时使用默认位置，
显式设置为空字符串或相对路径则视为配置错误。

路径不能包含当前系统的 PATH 分隔符：Windows 为分号，Linux/macOS 为冒号。
标准激活脚本无法将这样的目录作为单个条目加入 PATH，因此 uvg 会拒绝该配置。

环境名称必须以 ASCII 字母或数字开头，其余字符只能是 ASCII 字母、数字、点、下划线或连字符。
输入名称两端的空白会被去除。不支持使用符号链接或 Windows junction 作为环境目录。

环境目录是唯一事实来源，无需注册文件。空目录和不完整的环境目录也会出现在列表中；
无法读取 Python 版本时显示 `unknown`。激活时会检查所需的标准脚本。
如果列表中存在不合规名称或不支持的链接，仍会输出合法环境，同时向 stderr 报告异常条目，
并返回非零状态。

创建失败时会保留已产生的文件，并报告其位置；删除前请先检查这些文件。
删除操作会拒绝删除当前进程的 `VIRTUAL_ENV` 指向的环境，但不会跟踪其他终端的使用情况。
递归删除失败时，目录中的部分文件可能已经被删除。

## 激活与失败行为

激活、重复激活、切换和退出环境都使用环境自带的标准脚本。uvg 不维护自己的 PATH 备份、
提示符、嵌套栈或恢复状态。`uvg deactivate` 也可以退出外部的标准 venv，
且不要求 PATH 中仍能找到 uvg 可执行文件。

子 shell 可能继承 `VIRTUAL_ENV` 和 PATH，却没有继承 deactivate 函数。
在子 shell 中激活时，uvg 仍会加载标准脚本。退出时遵循该脚本保存的状态，
其中可能已经包含父 shell 的环境；uvg 无法重建父 shell 更早的 PATH。
`env current` 仅报告变量指向的环境目录，不代表 shell 的激活状态完整。

Bash 和 Zsh 会保留命令状态。PowerShell 包装函数仅保证数值状态 `$LASTEXITCODE`，
请勿通过 `$?`、`&&` 或 `||` 判断操作是否成功。

```powershell
uvg activate myenv
$uvgStatus = $LASTEXITCODE
if ($uvgStatus -ne 0) {
    # 在这里处理失败
}
```

## 升级迁移

本次 shell 集成重构包含不兼容变更：

- 移除 `uvg init` 和 `uvg setup`。请手动将旧初始化命令或生成的 hook 代码块替换为上方的加载片段。
- 原来的 `uvg activate --shell ...` 代码生成接口改为 `uvg shell activate <shell> <name>`。
- 将相对路径或空字符串形式的 `UVG_HOME` 改为绝对路径，或取消设置以使用默认位置。
- 包含当前系统 PATH 分隔符的路径也会被拒绝。
- 不再接受环境目录中的符号链接和 junction。uvg 不会移动或删除它们指向的目标，请手动整理这些条目。
- 替换初始化代码后，请重启已有的 shell。
