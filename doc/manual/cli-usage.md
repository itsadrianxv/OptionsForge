# 本项目 CLI 使用指南

本文面向在本地开发环境中使用本项目命令行入口的用户，介绍如何启动 CLI、各子命令的用途，以及一套推荐的日常使用流程。

## 1. CLI 是什么

本项目提供统一命令行入口 `option-scaffold`，用于完成以下常见工作：

- 创建整仓库级策略工作区
- 生成单个策略开发骨架
- 运行策略主程序
- 执行组合策略回测
- 校验配置、契约绑定与回测参数
- 诊断本地环境与依赖
- 浏览仓库内置示例

CLI 对应的两个入口如下：

- 可执行命令：`option-scaffold`
- Python 模块：`python -m src.cli.app`

如果你在本地开发阶段调试 CLI，推荐优先使用模块方式；如果你希望像正式命令一样直接执行，再安装可编辑脚本。

## 2. 环境准备

建议在使用 CLI 前准备好以下环境：

- Python `3.11+`
- 虚拟环境
- 项目依赖
- 可编辑安装（这样可以直接使用 `option-scaffold`）

在仓库根目录执行：

```powershell
cd D:\work_projects\option-strategy-scaffold

.\.venv\Scripts\Activate.ps1

pip install -r requirements.txt
pip install -e .
```

如果暂时不想执行 `pip install -e .`，也可以直接使用模块入口：

```powershell
python -m src.cli.app --help
```

## 3. 两种启动方式

### 3.1 开发态启动

最适合本地开发、调试和断点跟踪：

```powershell
python -m src.cli.app --help
```

优点：

- 不依赖系统 PATH
- 适合 IDE 调试
- 修改代码后可直接重新运行

### 3.2 命令态启动

执行过 `pip install -e .` 后，可直接使用：

```powershell
option-scaffold --help
```

如果当前 shell 还没有识别该命令，也可以直接调用虚拟环境中的可执行文件：

```powershell
.\.venv\Scripts\option-scaffold.exe --help
```

## 4. 根命令行为

根命令 `option-scaffold` 现在有两种常见行为：

### 4.1 交互终端中直接执行 `option-scaffold`

如果当前终端是交互式 TTY，并且没有传任何子命令和参数，会进入主菜单，而不是直接显示 help。

主菜单包含：

1. 创建策略工作区
2. 查看示例
3. 环境诊断
4. 退出

默认选项是“创建策略工作区”，所以直接回车就会进入 `create` 流程。

```powershell
option-scaffold
```

### 4.2 非交互环境或显式查看帮助

以下场景仍然保持普通 CLI 语义：

- `option-scaffold --help`
- `option-scaffold --version`
- `option-scaffold <子命令> ...`
- 非交互环境下执行 `option-scaffold`

例如：

```powershell
option-scaffold --help
option-scaffold --version
```

## 5. 查看总帮助与版本

```powershell
option-scaffold --help
option-scaffold --version
```

或：

```powershell
python -m src.cli.app --help
python -m src.cli.app --version
```

当前 CLI 提供以下子命令：

- `create`：创建整仓库级策略工作区
- `init`：生成单个策略开发骨架
- `run`：运行策略主程序
- `backtest`：执行组合策略回测
- `validate`：校验配置、契约绑定与可选回测参数
- `doctor`：诊断本地 CLI 环境、配置文件与运行依赖
- `examples`：列出并查看内置示例

查看某个子命令的帮助时，直接追加 `--help`：

```powershell
option-scaffold create --help
option-scaffold run --help
option-scaffold validate --help
option-scaffold doctor --help
```

## 6. 推荐使用流程

如果你第一次接触本项目，推荐按下面顺序使用：

```powershell
# 1) 查看 CLI 是否可正常启动
option-scaffold --help

# 2) 先诊断环境
option-scaffold doctor

# 3) 校验当前配置
option-scaffold validate --config config/strategy_config.toml

# 4) 浏览示例
option-scaffold examples

# 5) 创建新的策略工作区
option-scaffold create

# 6) 进入工作区后继续校验与运行
cd alpha_lab
option-scaffold validate --config config/strategy_config.toml
option-scaffold run --config config/strategy_config.toml
```

如果你更倾向于模块方式，也可以把上述命令全部替换为 `python -m src.cli.app ...`。

## 7. `create`：创建策略工作区

`create` 用于生成整仓库级期权策略工作区，是当前推荐的新项目创建入口。

### 7.1 交互式创建

最常用方式：

```powershell
option-scaffold create
```

如果当前在交互终端中运行，向导会按以下步骤引导你：

1. 项目命名
2. 选择策略预设
3. 是否自定义模块
4. 如选择自定义，则逐项确认 capability / option
5. 处理已有目录
6. 最终确认

当前默认行为如下：

- 默认项目名：`alpha_lab`
- 默认 preset：`custom`
- 默认不展开高级模块定制
- 生成前一定会出现最终确认页

### 7.2 ????

```powershell
# ????
option-scaffold create

# ??????
option-scaffold create -y

# ??????
option-scaffold create alpha_lab

# ?????????
option-scaffold create alpha_lab --preset ema-cross -d .\projects

# ???????
option-scaffold create alpha_lab --preset custom --with hedging --with-option vega-hedging --no-interactive

# ?????????
option-scaffold create alpha_lab --preset ema-cross --set setting.max_positions=8 --set runtime.log_level=DEBUG --set signal_kwargs.option_type=put --no-interactive
```

### 7.3 ????

- `NAME`??????????????????????? `alpha_lab`
- `-d, --destination`??????????????? `<destination>/<name>/`
- `--preset`???????? `custom`?`ema-cross`?`iv-rank`?`delta-neutral`
- `--with` / `--without`?? capability ?????????
- `--with-option` / `--without-option`?? capability ?????????
- `--set key=value`???????????????? `setting.*`?`runtime.*`????????????? preset ? `indicator_kwargs.*` / `signal_kwargs.*`
- `-y, --default`???????????????? `--set` ??
- `--no-interactive`?????????? flags?`--set` ???????
- `--clear`????????????
- `--overwrite`??????????????????
- `--force`???????????????

`--set` ???????????? TOML ??????

```powershell
option-scaffold create alpha_lab --preset ema-cross --set setting.max_positions=8 --set signal_kwargs.option_type=put --no-interactive
```

????????????? `--set`??????????????????????????????

### 7.4 创建完成后的 next steps

`create` 成功后，CLI 会直接输出一组可复制执行的 next steps：

```powershell
cd <project>
option-scaffold validate --config config/strategy_config.toml
option-scaffold run --config config/strategy_config.toml
```

生成出来的工作区 `README.md` 中也会使用同一套 next steps。

## 8. `init`：生成单个策略骨架

`init` 是较轻量的旧入口，适合只生成一个策略开发骨架，而不是整仓库工作区。

```powershell
option-scaffold init ema_breakout
```

常见用法：

```powershell
# 默认输出到 example/
option-scaffold init ema_breakout

# 指定输出目录
option-scaffold init ema_breakout --destination .\example

# 允许覆盖已存在目录
option-scaffold init ema_breakout --force
```

## 9. `validate`：校验配置与绑定关系

`validate` 用于在运行前检查策略配置、契约绑定，以及可选的回测参数覆盖。

```powershell
option-scaffold validate --config config/strategy_config.toml
```

常见示例：

```powershell
# 校验主配置
option-scaffold validate --config config/strategy_config.toml

# 携带覆盖配置一起校验
option-scaffold validate --config config/strategy_config.toml --override-config config/timeframe/5m.toml

# 连同回测参数一起校验
option-scaffold validate --config config/strategy_config.toml --start 2025-01-01 --end 2025-03-01 --capital 500000
```

## 10. `run`：运行策略主程序

`run` 会把参数转发到现有主程序入口，是最常用的执行命令。

最小可执行示例：

```powershell
option-scaffold run --config config/strategy_config.toml
```

常见示例：

```powershell
# 使用默认模式 standalone
option-scaffold run --config config/strategy_config.toml

# daemon 模式运行
option-scaffold run --mode daemon --config config/strategy_config.toml

# 无界面 + 模拟交易
option-scaffold run --config config/strategy_config.toml --no-ui --paper

# 指定日志级别和日志目录
option-scaffold run --config config/strategy_config.toml --log-level DEBUG --log-dir data/logs/demo
```

常用参数：

- `--mode`：`standalone` 或 `daemon`
- `--config`：主配置文件路径，默认 `config/strategy_config.toml`
- `--override-config`：覆盖配置文件路径
- `--log-level`：日志级别
- `--log-dir`：日志目录
- `--no-ui`：无界面模式运行
- `--paper`：启用模拟交易模式

## 11. `backtest`：执行回测

`backtest` 用于组合策略回测。

```powershell
option-scaffold backtest --config config/strategy_config.toml --start 2025-01-01 --end 2025-03-01
```

常见示例：

```powershell
option-scaffold backtest --config config/strategy_config.toml --start 2025-01-01 --end 2025-03-01

option-scaffold backtest --config config/strategy_config.toml --start 2025-01-01 --end 2025-03-01 --capital 500000 --rate 0.0001 --slippage 0.5 --size 100 --pricetick 0.1 --no-chart
```

## 12. `doctor`：诊断环境

`doctor` 用于检查 Python 版本、CLI 依赖、配置文件、数据库环境变量和网关环境等信息。

```powershell
option-scaffold doctor
```

常见示例：

```powershell
# 普通诊断
option-scaffold doctor

# 将警告也视为失败
option-scaffold doctor --strict

# 额外检查数据库连通性
option-scaffold doctor --check-db
```

这个命令特别适合在以下场景先执行一遍：

- 新机器首次拉起项目
- 刚改完 `.env` 或网关配置
- 运行或回测前怀疑依赖未装全

## 13. `examples`：浏览内置示例

`examples` 用于查看仓库中的示例策略目录和说明文档。

```powershell
option-scaffold examples
```

常见示例：

```powershell
# 列出全部示例
option-scaffold examples

# 查看某个示例详情
option-scaffold examples ema_breakout
```

输出通常会包含：

- 示例名称
- 示例路径
- 摘要
- 关键文件列表
- README 内容（如果存在）

## 14. 常见问题

### 14.1 直接执行 `option-scaffold` 为什么有时是菜单，有时是帮助？

因为根命令现在会根据当前环境自动判断：

- 交互终端 + 无参数：进入主菜单
- 非交互环境、显式 `--help`、显式子命令：按普通 CLI 行为处理

### 14.2 为什么 `create` 没有逐项问 capability / option？

因为当前默认路径会先问“是否自定义模块”，默认值是“否”。

如果你希望逐项控制能力组合：

- 在交互模式中选择“是”
- 或使用 `--with` / `--without` / `--with-option` / `--without-option` 配合 `--no-interactive`

### 14.3 `run` 提示缺少依赖怎么办？

先在虚拟环境中安装依赖：

```powershell
pip install -r requirements.txt
pip install -e .
```

然后重新执行：

```powershell
option-scaffold doctor
option-scaffold run --config config/strategy_config.toml
```

## 15. 一条最短上手路径

如果你只想快速上手，照着下面执行即可：

```powershell
option-scaffold doctor
option-scaffold create
cd alpha_lab
option-scaffold validate --config config/strategy_config.toml
option-scaffold run --config config/strategy_config.toml
```
