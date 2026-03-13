# TASK ROUTER

## How To Use This File

- Match the task to the closest pack first, then start from the recommended entrypoint.
- Default verification order: `python -m src.cli.app focus test` first, then `python -m src.cli.app focus test --full` only when needed.
- If the current focus is wide, start from one pack instead of scanning the full editable surface.

### `kernel`

- Task type: Core runtime flow and focus entrypoint
- Read first:
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
- Related config:
  - `config/strategy_config.toml`
  - `config/general/trading_target.toml`
  - `config/logging/logging.toml`
  - `config/subscription/subscription.toml`
  - `config/timeframe`
  - Config keys: `strategies`, `strategy_contracts`, `service_activation`, `observability`, `runtime`
- Recommended verification:
  - Smoke: `python -m src.cli.app focus test`
  - Relevant selectors:
    - `tests/strategy/application/test_market_workflow_pipeline.py`
    - `tests/strategy/infrastructure/bar_pipeline/test_bar_pipeline.py`
    - `tests/strategy/infrastructure/subscription/test_subscription_mode_engine.py`
    - `tests/strategy/infrastructure/utils/test_date_calculator.py`
    - `tests/cli/test_app.py`
  - Full: `python -m src.cli.app focus test --full`
- Common commands:
  - `python -m src.cli.app validate --config config/strategy_config.toml`
  - `python -m src.cli.app run --config config/strategy_config.toml --paper`
- Common mistakes:
  - do not push pack-specific logic back into broad entrypoints; prefer editing the concrete service or infrastructure implementation.
- Agent notes:
  - Use when: every strategy task depends on the kernel pack.
  - Read first: focus manifest, config/strategy_config.toml, src/strategy/strategy_entry.py.

### `selection`

- Task type: Underlying and contract selection
- Read first:
  - `src/strategy/domain/domain_service/selection`
- Related config:
  - `config/domain_service/selection`
  - Config keys: `service_activation.future_selection`, `service_activation.option_chain`, `service_activation.option_selector`
- Recommended verification:
  - Smoke: `python -m src.cli.app focus test`
  - Relevant selectors:
    - `tests/strategy/domain/domain_service/test_selection_integration.py`
  - Full: `python -m src.cli.app focus test --full`
- Common commands:
  - `python -m src.cli.app validate --config config/strategy_config.toml`
- Common mistakes:
  - do not hardcode selection logic into strategy_entry; keep it inside the selection service.
- Agent notes:
  - Use when: the task changes underlying selection, option-chain handling, or contract candidate rules.
  - Read first: src/strategy/domain/domain_service/selection and config/domain_service/selection.

### `pricing`

- Task type: Pricing and Greeks computation
- Read first:
  - `src/strategy/domain/domain_service/pricing`
- Related config:
  - `config/domain_service/pricing`
  - Config keys: `service_activation.pricing_engine`, `pricing_engine`
- Recommended verification:
  - Smoke: `python -m src.cli.app focus test`
  - Relevant selectors:
    - `tests/strategy/domain/domain_service/test_pricing_engine.py`
  - Full: `python -m src.cli.app focus test --full`
- Common commands:
  - `python -m src.cli.app validate --config config/strategy_config.toml`
- Common mistakes:
  - do not scatter pricing parameters across modules; keep them centralized in the pricing pack config.
- Agent notes:
  - Use when: the task changes pricing, implied volatility, or Greeks support.
  - Read first: src/strategy/domain/domain_service/pricing and config/domain_service/pricing.

### `risk`

- Task type: Portfolio risk and limits
- Read first:
  - `src/strategy/domain/domain_service/risk`
  - `src/strategy/domain/domain_service/combination`
- Related config:
  - `config/domain_service/risk`
  - Config keys: `service_activation.position_sizing`, `service_activation.greeks_calculator`, `service_activation.portfolio_risk`, `position_sizing`, `greeks_risk`, `combination_risk`
- Recommended verification:
  - Smoke: `python -m src.cli.app focus test`
  - Relevant selectors:
    - `tests/strategy/domain/domain_service/risk/test_risk_integration.py`
    - `tests/strategy/domain/domain_service/combination/test_combination_integration.py`
  - Full: `python -m src.cli.app focus test --full`
- Common commands:
  - `python -m src.cli.app validate --config config/strategy_config.toml`
- Common mistakes:
  - do not move risk decisions into CLI code or workflows; keep them inside concrete risk services.
- Agent notes:
  - Use when: the task changes position sizing, portfolio Greeks, stop logic, or risk budgets.
  - Read first: src/strategy/domain/domain_service/risk and src/strategy/domain/domain_service/combination.

### `execution`

- Task type: Order execution and scheduling
- Read first:
  - `src/strategy/domain/domain_service/execution`
- Related config:
  - `config/domain_service/execution`
  - Config keys: `service_activation.smart_order_executor`, `service_activation.advanced_order_scheduler`, `order_execution`, `advanced_orders`
- Recommended verification:
  - Smoke: `python -m src.cli.app focus test`
  - Relevant selectors:
    - `tests/strategy/domain/domain_service/test_execution_integration.py`
  - Full: `python -m src.cli.app focus test --full`
- Common commands:
  - `python -m src.cli.app run --config config/strategy_config.toml --paper`
- Common mistakes:
  - do not add facade or coordinator layers here; edit the concrete execution service directly.
- Agent notes:
  - Use when: the task changes smart order execution, scheduling, or execution control details.
  - Read first: src/strategy/domain/domain_service/execution and config/domain_service/execution.

### `hedging`

- Task type: Delta and Vega hedging
- Read first:
  - `src/strategy/domain/domain_service/hedging`
- Related config:
  - `config/strategy_config.toml`
  - Config keys: `service_activation.delta_hedging`, `service_activation.vega_hedging`, `hedging`
- Recommended verification:
  - Smoke: `python -m src.cli.app focus test`
  - Relevant selectors:
    - `tests/strategy/domain/domain_service/test_delta_hedging_service.py`
    - `tests/strategy/domain/domain_service/test_vega_hedging_service.py`
  - Full: `python -m src.cli.app focus test --full`
- Common commands:
  - `python -m src.cli.app run --config config/strategy_config.toml --paper`
- Common mistakes:
  - do not scatter hedging thresholds through business code; keep them in config-driven hedging services.
- Agent notes:
  - Use when: the task changes Delta hedging, Vega hedging, or hedging thresholds.
  - Read first: src/strategy/domain/domain_service/hedging and the hedging section in config/strategy_config.toml.

### `monitoring`

- Task type: Monitoring, persistence, and observability
- Read first:
  - `src/strategy/infrastructure/monitoring`
  - `src/strategy/infrastructure/persistence`
- Related config:
  - `config/strategy_config.toml`
  - Config keys: `service_activation.monitoring`, `service_activation.decision_observability`, `observability`
- Recommended verification:
  - Smoke: `python -m src.cli.app focus test`
  - Relevant selectors:
    - `tests/strategy/infrastructure/monitoring/test_strategy_monitor_serialization.py`
    - `tests/strategy/infrastructure/persistence/test_state_repository.py`
  - Full: `python -m src.cli.app focus test --full`
- Common commands:
  - `python -m src.cli.app run --config config/strategy_config.toml --paper`
- Common mistakes:
  - do not push monitoring or storage details into domain services; keep them in infrastructure.
- Agent notes:
  - Use when: the task changes monitoring, snapshots, persistence, or observability output.
  - Read first: src/strategy/infrastructure/monitoring and src/strategy/infrastructure/persistence.

### `web`

- Task type: Read-only visual monitoring
- Read first:
  - `src/web`
- Related config:
  - `config/strategy_config.toml`
  - Config keys: `runtime.log_dir`
- Recommended verification:
  - Smoke: `python -m src.cli.app focus test`
  - Relevant selectors:
    - `tests/web/test_monitor_template.py`
    - `tests/web/test_strategy_state_reader.py`
  - Full: `python -m src.cli.app focus test --full`
- Common commands:
  - `python src/web/app.py`
- Common mistakes:
  - do not move strategy decision logic into the web layer; web should stay read-only and presentational.
- Agent notes:
  - Use when: the task changes the monitoring UI, state readers, or frontend presentation.
  - Read first: src/web and tests/web.

### `deploy`

- Task type: Container and environment setup
- Read first:
  - `.dockerignore`
  - `.env.example`
  - `deploy`
- Related config:
  - `.env.example`
  - Config keys: none
- Recommended verification:
  - Smoke: `python -m src.cli.app focus test`
  - Relevant selectors:
    - none
  - Full: `python -m src.cli.app focus test --full`
- Common commands:
  - `docker compose --env-file deploy/.env -f deploy/docker-compose.yml up -d --build`
- Common mistakes:
  - do not start with deploy changes for local strategy iteration; confirm the runtime path and focus assets first.
- Agent notes:
  - Use when: the task changes container setup, database integration, or multi-service startup.
  - Read first: deploy/docker-compose.yml, deploy/.env.example, and deploy/Dockerfile.

### `backtest`

- Task type: Backtest flow and parameter verification
- Read first:
  - `src/backtesting`
- Related config:
  - `config/strategy_config.toml`
  - Config keys: `strategies`, `service_activation`
- Recommended verification:
  - Smoke: `python -m src.cli.app focus test`
  - Relevant selectors:
    - `tests/backtesting/test_cli.py`
    - `tests/backtesting/test_runner.py`
  - Full: `python -m src.cli.app focus test --full`
- Common commands:
  - `python -m src.cli.app backtest --config config/strategy_config.toml --start 2025-01-01 --end 2025-03-01 --no-chart`
- Common mistakes:
  - do not duplicate strategy logic just for backtest; reuse the main strategy contract and config.
- Agent notes:
  - Use when: the task needs execution evidence for strategy logic, contract discovery, or parameter effects.
  - Read first: src/backtesting and tests/backtesting.
