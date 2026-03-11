# TASK ROUTER

## 使用方式

- 先匹配最接近的任务类型，再按首看入口进入代码。
- 默认先跑 `option-scaffold focus test`，通过后再补跑 `option-scaffold focus test --full`。
- 如果当前焦点偏宽，先从单个 pack 开始，不要一上来横扫整个 Editable Surface。

### `kernel`

- 任务类型: 主运行链路与焦点入口
- 首看入口:
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
- 相关配置:
  - `config/strategy_config.toml`
  - `config/general/trading_target.toml`
  - `config/logging/logging.toml`
  - `config/subscription/subscription.toml`
  - `config/timeframe`
  - 配置键: `strategies`, `strategy_contracts`, `service_activation`, `observability`, `runtime`
- 推荐测试:
  - Smoke: `option-scaffold focus test`
  - 相关选择器:
    - `tests/strategy/application/test_market_workflow_pipeline.py`
    - `tests/strategy/infrastructure/bar_pipeline/test_bar_pipeline.py`
    - `tests/strategy/infrastructure/subscription/test_subscription_mode_engine.py`
    - `tests/strategy/infrastructure/utils/test_date_calculator.py`
    - `tests/cli/test_app.py`
  - Full: `option-scaffold focus test --full`
- 常用命令:
  - `option-scaffold validate --config config/strategy_config.toml`
  - `option-scaffold run --config config/strategy_config.toml --paper`
- 常见误改:
  - 不要把 pack 级逻辑塞回总入口，优先直接修改具体领域服务或基础设施实现。
- Agent 提示:
  - 启用时机：任何策略都会依赖 kernel。
  - 先看文件：focus manifest、config/strategy_config.toml、src/strategy/strategy_entry.py。

### `selection`

- 任务类型: 选标与合约筛选
- 首看入口:
  - `src/strategy/domain/domain_service/selection`
- 相关配置:
  - `config/domain_service/selection`
  - 配置键: `service_activation.future_selection`, `service_activation.option_chain`, `service_activation.option_selector`
- 推荐测试:
  - Smoke: `option-scaffold focus test`
  - 相关选择器:
    - `tests/strategy/domain/domain_service/test_selection_integration.py`
  - Full: `option-scaffold focus test --full`
- 常用命令:
  - `option-scaffold validate --config config/strategy_config.toml`
- 常见误改:
  - 不要把选标逻辑硬编码进 strategy_entry，优先收敛在 selection 服务里。
- Agent 提示:
  - 启用时机：需要决定期货主力、期权链或合约筛选规则时。
  - 先看文件：src/strategy/domain/domain_service/selection 与 config/domain_service/selection。

### `pricing`

- 任务类型: 定价与 Greeks 计算
- 首看入口:
  - `src/strategy/domain/domain_service/pricing`
- 相关配置:
  - `config/domain_service/pricing`
  - 配置键: `service_activation.pricing_engine`, `pricing_engine`
- 推荐测试:
  - Smoke: `option-scaffold focus test`
  - 相关选择器:
    - `tests/strategy/domain/domain_service/test_pricing_engine.py`
  - Full: `option-scaffold focus test --full`
- 常用命令:
  - `option-scaffold validate --config config/strategy_config.toml`
- 常见误改:
  - 不要把 pricing 参数散落在多个模块，优先通过 pricing pack 配置集中管理。
- Agent 提示:
  - 启用时机：需要定价、隐波或 Greeks 估值支持时。
  - 先看文件：src/strategy/domain/domain_service/pricing 与 config/domain_service/pricing。

### `risk`

- 任务类型: 组合风控与限额控制
- 首看入口:
  - `src/strategy/domain/domain_service/risk`
  - `src/strategy/domain/domain_service/combination`
- 相关配置:
  - `config/domain_service/risk`
  - 配置键: `service_activation.position_sizing`, `service_activation.greeks_calculator`, `service_activation.portfolio_risk`, `position_sizing`, `greeks_risk`, `combination_risk`
- 推荐测试:
  - Smoke: `option-scaffold focus test`
  - 相关选择器:
    - `tests/strategy/domain/domain_service/risk/test_risk_integration.py`
    - `tests/strategy/domain/domain_service/combination/test_combination_integration.py`
  - Full: `option-scaffold focus test --full`
- 常用命令:
  - `option-scaffold validate --config config/strategy_config.toml`
- 常见误改:
  - 不要把风控判断回塞到 CLI 或 workflow，保持在具体 risk 服务内。
- Agent 提示:
  - 启用时机：需要仓位控制、组合 Greeks、止损或风险预算时。
  - 先看文件：src/strategy/domain/domain_service/risk、src/strategy/domain/domain_service/combination。

### `execution`

- 任务类型: 下单执行与排程
- 首看入口:
  - `src/strategy/domain/domain_service/execution`
- 相关配置:
  - `config/domain_service/execution`
  - 配置键: `service_activation.smart_order_executor`, `service_activation.advanced_order_scheduler`, `order_execution`, `advanced_orders`
- 推荐测试:
  - Smoke: `option-scaffold focus test`
  - 相关选择器:
    - `tests/strategy/domain/domain_service/test_execution_integration.py`
  - Full: `option-scaffold focus test --full`
- 常用命令:
  - `option-scaffold run --config config/strategy_config.toml --paper`
- 常见误改:
  - 不要新增 facade/coordinator 抽象层，直接修改具体执行服务。
- Agent 提示:
  - 启用时机：需要智能下单、排程或更细粒度执行控制时。
  - 先看文件：src/strategy/domain/domain_service/execution 与 config/domain_service/execution。

### `hedging`

- 任务类型: Delta / Vega 对冲
- 首看入口:
  - `src/strategy/domain/domain_service/hedging`
- 相关配置:
  - `config/strategy_config.toml`
  - 配置键: `service_activation.delta_hedging`, `service_activation.vega_hedging`, `hedging`
- 推荐测试:
  - Smoke: `option-scaffold focus test`
  - 相关选择器:
    - `tests/strategy/domain/domain_service/test_delta_hedging_service.py`
    - `tests/strategy/domain/domain_service/test_vega_hedging_service.py`
  - Full: `option-scaffold focus test --full`
- 常用命令:
  - `option-scaffold run --config config/strategy_config.toml --paper`
- 常见误改:
  - 不要把对冲阈值散落到业务代码里，优先保持在配置驱动的 hedging 服务中。
- Agent 提示:
  - 启用时机：需要 Delta / Vega 对冲或 gamma scalping 时。
  - 先看文件：src/strategy/domain/domain_service/hedging 与 config/strategy_config.toml 下的 hedging 配置。

### `monitoring`

- 任务类型: 监控、日志与状态落盘
- 首看入口:
  - `src/strategy/infrastructure/monitoring`
  - `src/strategy/infrastructure/persistence`
- 相关配置:
  - `config/strategy_config.toml`
  - 配置键: `service_activation.monitoring`, `service_activation.decision_observability`, `observability`
- 推荐测试:
  - Smoke: `option-scaffold focus test`
  - 相关选择器:
    - `tests/strategy/infrastructure/monitoring/test_strategy_monitor_serialization.py`
    - `tests/strategy/infrastructure/persistence/test_state_repository.py`
  - Full: `option-scaffold focus test --full`
- 常用命令:
  - `option-scaffold run --config config/strategy_config.toml --paper`
- 常见误改:
  - 不要把监控存储细节混入 domain service，保持在基础设施层。
- Agent 提示:
  - 启用时机：需要状态落盘、决策日志、快照或监控序列化时。
  - 先看文件：src/strategy/infrastructure/monitoring、src/strategy/infrastructure/persistence。

### `web`

- 任务类型: 可视化展示与快照读取
- 首看入口:
  - `src/web`
- 相关配置:
  - `config/strategy_config.toml`
  - 配置键: `runtime.log_dir`
- 推荐测试:
  - Smoke: `option-scaffold focus test`
  - 相关选择器:
    - `tests/web/test_monitor_template.py`
    - `tests/web/test_strategy_state_reader.py`
  - Full: `option-scaffold focus test --full`
- 常用命令:
  - `python src/web/app.py`
- 常见误改:
  - 不要把策略判断逻辑挪到 Web 层，Web 只负责读状态和展示。
- Agent 提示:
  - 启用时机：需要可视化监控页面、快照读取或前端展示时。
  - 先看文件：src/web 与 tests/web。

### `deploy`

- 任务类型: 容器化与环境装配
- 首看入口:
  - `.dockerignore`
  - `.env.example`
  - `deploy`
- 相关配置:
  - `.env.example`
  - 配置键: 无
- 推荐测试:
  - Smoke: `option-scaffold focus test`
  - 相关选择器:
    - 无
  - Full: `option-scaffold focus test --full`
- 常用命令:
  - `docker compose --env-file deploy/.env -f deploy/docker-compose.yml up -d --build`
- 常见误改:
  - 本地策略迭代不必先动 deploy，优先确认运行链路和焦点文档。
- Agent 提示:
  - 启用时机：需要容器化、数据库联调或 runner + monitor 一起启动时。
  - 先看文件：deploy/docker-compose.yml、deploy/.env.example、deploy/Dockerfile。

### `backtest`

- 任务类型: 回测链路与参数验证
- 首看入口:
  - `src/backtesting`
- 相关配置:
  - `config/strategy_config.toml`
  - 配置键: `strategies`, `service_activation`
- 推荐测试:
  - Smoke: `option-scaffold focus test`
  - 相关选择器:
    - `tests/backtesting/test_cli.py`
    - `tests/backtesting/test_runner.py`
  - Full: `option-scaffold focus test --full`
- 常用命令:
  - `option-scaffold backtest --config config/strategy_config.toml --start 2025-01-01 --end 2025-03-01 --no-chart`
- 常见误改:
  - 不要为回测单独复制一套策略逻辑，优先复用主策略契约与配置。
- Agent 提示:
  - 启用时机：需要快速验证策略逻辑、合约发现和参数效果时。
  - 先看文件：src/backtesting、tests/backtesting。
