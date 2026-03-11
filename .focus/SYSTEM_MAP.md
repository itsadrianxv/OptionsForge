# SYSTEM MAP

## Current Focus

- 策略: `main`
- 交易标的: `option-universe`
- 策略类型: `custom`
- 运行模式: `standalone`
- Focus Manifest: `focus/strategies/main/strategy.manifest.toml`
- Pack 链路: `kernel` -> `selection` -> `pricing` -> `risk` -> `execution` -> `hedging` -> `monitoring` -> `web` -> `deploy` -> `backtest`

## 建议阅读顺序

1. `focus/strategies/main/strategy.manifest.toml`
2. `src/strategy/strategy_entry.py`
3. `src/strategy/application`
4. `src/strategy/domain`
5. `config/strategy_config.toml`

## 运行链路

1. `option-scaffold` / `option-scaffold focus` 作为统一入口
2. `src/cli/app.py` 把命令分发到 `run`、`backtest`、`validate` 与 `focus`
3. `src/main/main.py` 负责主运行链路与启动编排
4. `src/strategy/strategy_entry.py` 连接 application / domain / infrastructure
5. 当前启用 pack 在领域服务、监控、回测、Web 与部署侧补齐能力

## Pack 说明

### `kernel`

- 依赖: 无
- 配置键: `strategies`, `strategy_contracts`, `service_activation`, `observability`, `runtime`
- 所属路径:
- `src/strategy/strategy_entry.py`
- `src/strategy/application`
- `src/strategy/domain/entity`
- `src/strategy/domain/value_object`
- `src/strategy/domain/domain_service/signal`
- `src/strategy/infrastructure/bar_pipeline`
- `src/strategy/infrastructure/subscription`
- `src/strategy/infrastructure/utils`
- `src/main/main.py`
- `src/main/bootstrap`
- `src/main/config`
- `src/main/process`
- `src/main/utils`
- `src/cli`
- `config/strategy_config.toml`
- `config/general/trading_target.toml`
- `config/logging/logging.toml`
- `config/subscription/subscription.toml`
- `config/timeframe`
- `tests/strategy/application`
- `tests/strategy/domain/entity`
- `tests/strategy/domain/value_object`
- `tests/strategy/infrastructure/bar_pipeline`
- `tests/strategy/infrastructure/subscription`
- `tests/strategy/infrastructure/utils`
- `tests/cli/test_app.py`
- 常用命令:
  - `option-scaffold validate --config config/strategy_config.toml`
  - `option-scaffold run --config config/strategy_config.toml --paper`
- Agent 提示:
  - 启用时机：任何策略都会依赖 kernel。
  - 先看文件：focus manifest、config/strategy_config.toml、src/strategy/strategy_entry.py。
  - 常见误改：不要把 pack 级逻辑塞回总入口，优先直接修改具体领域服务或基础设施实现。

### `selection`

- 依赖: `kernel`
- 配置键: `service_activation.future_selection`, `service_activation.option_chain`, `service_activation.option_selector`
- 所属路径:
- `src/strategy/domain/domain_service/selection`
- `config/domain_service/selection`
- `tests/strategy/domain/domain_service/test_selection_integration.py`
- 常用命令:
  - `option-scaffold validate --config config/strategy_config.toml`
- Agent 提示:
  - 启用时机：需要决定期货主力、期权链或合约筛选规则时。
  - 先看文件：src/strategy/domain/domain_service/selection 与 config/domain_service/selection。
  - 常见误改：不要把选标逻辑硬编码进 strategy_entry，优先收敛在 selection 服务里。

### `pricing`

- 依赖: `kernel`, `selection`
- 配置键: `service_activation.pricing_engine`, `pricing_engine`
- 所属路径:
- `src/strategy/domain/domain_service/pricing`
- `config/domain_service/pricing`
- `tests/strategy/domain/domain_service/test_pricing_engine.py`
- `tests/strategy/domain/domain_service/test_pricing_engine_config_properties.py`
- `tests/strategy/domain/domain_service/test_pricing_engine_properties.py`
- `tests/strategy/domain/domain_service/test_pricing_properties.py`
- 常用命令:
  - `option-scaffold validate --config config/strategy_config.toml`
- Agent 提示:
  - 启用时机：需要定价、隐波或 Greeks 估值支持时。
  - 先看文件：src/strategy/domain/domain_service/pricing 与 config/domain_service/pricing。
  - 常见误改：不要把 pricing 参数散落在多个模块，优先通过 pricing pack 配置集中管理。

### `risk`

- 依赖: `kernel`, `selection`
- 配置键: `service_activation.position_sizing`, `service_activation.greeks_calculator`, `service_activation.portfolio_risk`, `position_sizing`, `greeks_risk`, `combination_risk`
- 所属路径:
- `src/strategy/domain/domain_service/risk`
- `src/strategy/domain/domain_service/combination`
- `config/domain_service/risk`
- `tests/strategy/domain/domain_service/risk`
- `tests/strategy/domain/domain_service/combination`
- 常用命令:
  - `option-scaffold validate --config config/strategy_config.toml`
- Agent 提示:
  - 启用时机：需要仓位控制、组合 Greeks、止损或风险预算时。
  - 先看文件：src/strategy/domain/domain_service/risk、src/strategy/domain/domain_service/combination。
  - 常见误改：不要把风控判断回塞到 CLI 或 workflow，保持在具体 risk 服务内。

### `execution`

- 依赖: `kernel`, `risk`
- 配置键: `service_activation.smart_order_executor`, `service_activation.advanced_order_scheduler`, `order_execution`, `advanced_orders`
- 所属路径:
- `src/strategy/domain/domain_service/execution`
- `config/domain_service/execution`
- `tests/strategy/domain/domain_service/test_execution_config_properties.py`
- `tests/strategy/domain/domain_service/test_execution_coordinator_properties.py`
- `tests/strategy/domain/domain_service/test_execution_integration.py`
- 常用命令:
  - `option-scaffold run --config config/strategy_config.toml --paper`
- Agent 提示:
  - 启用时机：需要智能下单、排程或更细粒度执行控制时。
  - 先看文件：src/strategy/domain/domain_service/execution 与 config/domain_service/execution。
  - 常见误改：不要新增 facade/coordinator 抽象层，直接修改具体执行服务。

### `hedging`

- 依赖: `kernel`, `risk`, `execution`
- 配置键: `service_activation.delta_hedging`, `service_activation.vega_hedging`, `hedging`
- 所属路径:
- `src/strategy/domain/domain_service/hedging`
- `config/strategy_config.toml`
- `tests/strategy/domain/domain_service/test_delta_hedging_service.py`
- `tests/strategy/domain/domain_service/test_vega_hedging_service.py`
- 常用命令:
  - `option-scaffold run --config config/strategy_config.toml --paper`
- Agent 提示:
  - 启用时机：需要 Delta / Vega 对冲或 gamma scalping 时。
  - 先看文件：src/strategy/domain/domain_service/hedging 与 config/strategy_config.toml 下的 hedging 配置。
  - 常见误改：不要把对冲阈值散落到业务代码里，优先保持在配置驱动的 hedging 服务中。

### `monitoring`

- 依赖: `kernel`
- 配置键: `service_activation.monitoring`, `service_activation.decision_observability`, `observability`
- 所属路径:
- `src/strategy/infrastructure/monitoring`
- `src/strategy/infrastructure/persistence`
- `tests/strategy/infrastructure/monitoring`
- `tests/strategy/infrastructure/persistence`
- 常用命令:
  - `option-scaffold run --config config/strategy_config.toml --paper`
- Agent 提示:
  - 启用时机：需要状态落盘、决策日志、快照或监控序列化时。
  - 先看文件：src/strategy/infrastructure/monitoring、src/strategy/infrastructure/persistence。
  - 常见误改：不要把监控存储细节混入 domain service，保持在基础设施层。

### `web`

- 依赖: `kernel`, `monitoring`
- 配置键: `runtime.log_dir`
- 所属路径:
- `src/web`
- `tests/web`
- 常用命令:
  - `python src/web/app.py`
- Agent 提示:
  - 启用时机：需要可视化监控页面、快照读取或前端展示时。
  - 先看文件：src/web 与 tests/web。
  - 常见误改：不要把策略判断逻辑挪到 Web 层，Web 只负责读状态和展示。

### `deploy`

- 依赖: `kernel`, `monitoring`, `web`
- 配置键: 无
- 所属路径:
- `.dockerignore`
- `.env.example`
- `deploy`
- 常用命令:
  - `docker compose --env-file deploy/.env -f deploy/docker-compose.yml up -d --build`
- Agent 提示:
  - 启用时机：需要容器化、数据库联调或 runner + monitor 一起启动时。
  - 先看文件：deploy/docker-compose.yml、deploy/.env.example、deploy/Dockerfile。
  - 常见误改：本地策略迭代不必先动 deploy，优先确认运行链路和焦点文档。

### `backtest`

- 依赖: `kernel`, `selection`
- 配置键: `strategies`, `service_activation`
- 所属路径:
- `src/backtesting`
- `tests/backtesting`
- 常用命令:
  - `option-scaffold backtest --config config/strategy_config.toml --start 2025-01-01 --end 2025-03-01 --no-chart`
- Agent 提示:
  - 启用时机：需要快速验证策略逻辑、合约发现和参数效果时。
  - 先看文件：src/backtesting、tests/backtesting。
  - 常见误改：不要为回测单独复制一套策略逻辑，优先复用主策略契约与配置。
