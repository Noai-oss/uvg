# uvg 使用参考

[English](reference.md) | [简体中文](reference_zh.md) · [返回 README](../README_zh.md)

本页说明目录配置、shell 行为和脚本接口。安装和首次配置请从
[README](../README_zh.md#shell-集成) 开始。

## 环境目录

环境是 `~/.uvg/venvs` 下的普通一级目录。设置 `UVG_HOME` 后，环境改为保存在
`UVG_HOME/venvs` 下。

- `UVG_HOME` 展开 `~` 后必须是绝对路径。只有未设置时才使用默认位置；空字符串或相对路径
  都是配置错误。
- 路径不能包含当前系统的 PATH 分隔符：Windows 为分号，Linux/macOS 为冒号。
  标准激活脚本无法将这样的路径作为单个条目加入 PATH。
- 环境名称必须以 ASCII 字母或数字开头，其余字符只能是 ASCII 字母、数字、点、下划线或
  连字符。输入名称两端的空白会被去除。
- 不支持使用符号链接或 Windows junction 作为环境目录。

环境无需注册文件。空目录和不完整的环境目录也会出现在 `uvg env list` 中；无法读取 Python
版本时显示 `unknown`。激活时会检查所需的标准脚本。如果列表中存在不合规名称或不支持的
链接，仍会输出合法环境，同时向 stderr 报告异常条目，并返回非零状态。

`uvg env dir` 输出配置的目录路径，不创建目录。列出尚不存在的目录会得到空结果；
目录不可读则会报错。

## 创建与删除环境

创建时调用 `uv venv --seed`，指定 Python 版本时附加 `--python`。创建环境需要 uv；
查询和激活已有环境不要求 PATH 中存在 uv。

创建失败时会保留已产生的文件，并报告其位置；删除前请先检查这些文件。
`uvg remove` 会请求确认，除非指定了 `-y`；取消删除会保留环境，并以成功状态退出。

删除操作会拒绝删除当前进程的 `VIRTUAL_ENV` 指向的环境，但不会跟踪其他终端的使用情况。
递归删除失败时，目录中的部分文件可能已经被删除。

## Shell 行为

支持的平台和 shell 加载片段见 [README](../README_zh.md#shell-集成)。

激活、重复激活、切换和退出环境都使用环境自带的标准脚本。`uvg deactivate` 也可以退出外部
的标准 venv，且不要求 PATH 中仍能找到 uvg 可执行文件。当前 shell 没有 deactivate 函数时，
它会报错。

子 shell 可能继承 `VIRTUAL_ENV` 和 PATH，却没有继承 deactivate 函数。在子 shell 中激活时，
uvg 仍会加载标准脚本。退出时遵循该脚本保存的状态，其中可能已经包含父 shell 的环境；
uvg 无法重建父 shell 更早的 PATH，也不维护环境嵌套栈。
`uvg env current` 识别 `VIRTUAL_ENV` 指向的普通一级环境目录，不检查 shell 的完整激活状态。

### 退出状态

Bash 和 Zsh 会保留命令状态。PowerShell 包装函数仅保证数值状态 `$LASTEXITCODE`，
请勿通过 `$?`、`&&` 或 `||` 判断操作是否成功。

```powershell
uvg activate myenv
$uvgStatus = $LASTEXITCODE
if ($uvgStatus -ne 0) {
    # 在这里处理失败
}
```

### Shell 代码接口

这些命令输出供调用方执行的代码，本身不会激活父 shell 中的环境。

| 命令 | 输出 |
| --- | --- |
| `uvg shell hook <shell>` | 运行时 shell 函数 |
| `uvg shell activate <shell> <name>` | 用于加载环境标准激活脚本的代码 |

`<shell>` 可取 `bash`、`zsh` 或 `pwsh`。成功时，stdout 仅包含 UTF-8 编码、LF 换行的代码；
失败时，诊断写入 stderr，并返回非零状态。加载片段和 hook 都不会执行代码生成进程失败时
输出的内容。标准脚本自身执行失败时会报告失败，但不会回滚已经发生的 shell 状态变化。

## 从源码安装

如果已经在本地获取了仓库代码，可以在仓库根目录执行：

```bash
uv tool install .
```
