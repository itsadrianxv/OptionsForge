## 1. 项目目录

```mermaid
flowchart TD
    ROOT[option-strategy-scaffold]
    ROOT --> CFG[config/]
    ROOT --> SRC[src/]
    ROOT --> TESTS[tests/]
    ROOT --> SCRIPTS[scripts/]
    ROOT --> DEPLOY[deploy/]
    ROOT --> DOC[doc/]

    CFG --> CFG_CORE[strategy_config.toml]
    CFG --> CFG_GENERAL[general/]
    CFG --> CFG_SUB[subscription/]
    CFG --> CFG_DOMAIN[domain_service/]
    CFG --> CFG_TIMEFRAME[timeframe/]

    SRC --> SRC_MAIN[src/main/]
    SRC --> SRC_STRATEGY[src/strategy/]
    SRC --> SRC_BACKTEST[src/backtesting/]
    SRC --> SRC_WEB[src/web/]
```

## 2. 在 config 目录下配置策略的方法

```mermaid
flowchart LR
    A[config/general/trading_target.toml<br/>配置交易品种 targets] --> B[config/strategy_config.toml<br/>配置 strategies.setting / runtime / risk]
    B --> C[config/domain_service/**/*.toml<br/>配置选券/风控/执行/定价细节]
    C --> D[config/subscription/subscription.toml<br/>配置订阅模式与收敛规则]
    D --> E[可选: config/timeframe/*.toml<br/>覆盖 bar_window / strategy_name]
    E --> F[运行: python -m src.main.main --mode standalone --config config/strategy_config.toml --override-config config/timeframe/15m.toml]
```

配置顺序建议：
1. 先改 `config/general/trading_target.toml` 的 `targets`，确定要交易的品种。
2. 再改 `config/strategy_config.toml` 的 `[[strategies]]` 与 `[strategies.setting]`（如 `max_positions`、`position_ratio`、`strike_level`、`bar_window`）。
3. 按需改 `config/domain_service/` 下各模块 TOML（`selection`、`risk`、`execution`、`pricing`）。
4. 需要自动订阅收敛时，改 `config/subscription/subscription.toml` 的 `enabled`、`enabled_modes` 等参数。
5. 需要多周期策略时，在 `config/timeframe/` 新建覆盖文件并通过 `--override-config` 传入。

## 3. 以本策略作为模板仓库搭建自己的期权交易策略的指南

```mermaid
flowchart TD
    T1[1. 基于模板创建新仓库] --> T2[2. 替换策略实现]
    T2 --> T3[3. 调整配置]
    T3 --> T4[4. 补充测试]
    T4 --> T5[5. 本地联调并运行]
    T5 --> T6[6. 迭代策略参数与风控阈值]
```

落地步骤：
1. 用该仓库创建新仓库（GitHub `Use this template` 或本地 `git clone` 后改远端）。
2. 在 `src/strategy/domain/domain_service/signal/` 实现你的信号逻辑（`IndicatorService`、`SignalService`）。
3. 在 `src/strategy/strategy_entry.py` 保持入口类可用，并确保 `config/strategy_config.toml` 的 `class_name` 与策略参数匹配。
4. 按你的交易标的与风控需求，完整调整 `config/` 下文件（至少 `strategy_config.toml`、`trading_target.toml`、`domain_service/*.toml`）。
5. 在 `tests/strategy/` 与 `tests/main/` 增加或修改对应测试，覆盖开平仓、风控和配置加载。
6. 使用以下命令启动验证：

```bash
python -m src.main.main --mode standalone --config config/strategy_config.toml
```
