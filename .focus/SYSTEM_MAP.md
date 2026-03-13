# SYSTEM MAP

## Current Focus

- Strategy: `main`
- Trading target: `option-universe`
- Strategy type: `custom`
- Run mode: `standalone`
- Focus Manifest: `focus/strategies/main/strategy.manifest.toml`
- Pack chain: `kernel` -> `selection` -> `pricing` -> `risk` -> `execution` -> `hedging` -> `monitoring` -> `web` -> `deploy` -> `backtest`

## Read In This Order

1. `focus/strategies/main/strategy.manifest.toml`
2. `src/strategy/strategy_entry.py`
3. `src/strategy/application`
4. `src/strategy/domain`
5. `config/strategy_config.toml`

## Runtime Chain

1. Source-checkout default: `python -m src.cli.app`.
2. Installed alias: `option-scaffold`.
3. Run CLI commands from `repo-root`.
4. `src/cli/app.py` routes commands to `forge`, `focus`, `run`, `backtest`, `validate`, and supporting commands.
5. `src/main/main.py` orchestrates runtime startup.
6. `src/strategy/strategy_entry.py` connects application, domain, and infrastructure layers.
7. Enabled packs extend the runtime with domain logic, monitoring, backtest, web, and deploy capabilities.

## Pack Notes

### `kernel`

- Depends on: none
- Config keys: `strategies`, `strategy_contracts`, `service_activation`, `observability`, `runtime`
- Owned paths:
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
- Common commands:
  - `python -m src.cli.app validate --config config/strategy_config.toml`
  - `python -m src.cli.app run --config config/strategy_config.toml --paper`
- Agent notes:
  - Use when: every strategy task depends on the kernel pack.
  - Read first: focus manifest, config/strategy_config.toml, src/strategy/strategy_entry.py.
  - Common mistake: do not push pack-specific logic back into broad entrypoints; prefer editing the concrete service or infrastructure implementation.

### `selection`

- Depends on: `kernel`
- Config keys: `service_activation.future_selection`, `service_activation.option_chain`, `service_activation.option_selector`
- Owned paths:
- `src/strategy/domain/domain_service/selection`
- `config/domain_service/selection`
- `tests/strategy/domain/domain_service/test_selection_integration.py`
- Common commands:
  - `python -m src.cli.app validate --config config/strategy_config.toml`
- Agent notes:
  - Use when: the task changes underlying selection, option-chain handling, or contract candidate rules.
  - Read first: src/strategy/domain/domain_service/selection and config/domain_service/selection.
  - Common mistake: do not hardcode selection logic into strategy_entry; keep it inside the selection service.

### `pricing`

- Depends on: `kernel`, `selection`
- Config keys: `service_activation.pricing_engine`, `pricing_engine`
- Owned paths:
- `src/strategy/domain/domain_service/pricing`
- `config/domain_service/pricing`
- `tests/strategy/domain/domain_service/test_pricing_engine.py`
- `tests/strategy/domain/domain_service/test_pricing_engine_config_properties.py`
- `tests/strategy/domain/domain_service/test_pricing_engine_properties.py`
- `tests/strategy/domain/domain_service/test_pricing_properties.py`
- Common commands:
  - `python -m src.cli.app validate --config config/strategy_config.toml`
- Agent notes:
  - Use when: the task changes pricing, implied volatility, or Greeks support.
  - Read first: src/strategy/domain/domain_service/pricing and config/domain_service/pricing.
  - Common mistake: do not scatter pricing parameters across modules; keep them centralized in the pricing pack config.

### `risk`

- Depends on: `kernel`, `selection`
- Config keys: `service_activation.position_sizing`, `service_activation.greeks_calculator`, `service_activation.portfolio_risk`, `position_sizing`, `greeks_risk`, `combination_risk`
- Owned paths:
- `src/strategy/domain/domain_service/risk`
- `src/strategy/domain/domain_service/combination`
- `config/domain_service/risk`
- `tests/strategy/domain/domain_service/risk`
- `tests/strategy/domain/domain_service/combination`
- Common commands:
  - `python -m src.cli.app validate --config config/strategy_config.toml`
- Agent notes:
  - Use when: the task changes position sizing, portfolio Greeks, stop logic, or risk budgets.
  - Read first: src/strategy/domain/domain_service/risk and src/strategy/domain/domain_service/combination.
  - Common mistake: do not move risk decisions into CLI code or workflows; keep them inside concrete risk services.

### `execution`

- Depends on: `kernel`, `risk`
- Config keys: `service_activation.smart_order_executor`, `service_activation.advanced_order_scheduler`, `order_execution`, `advanced_orders`
- Owned paths:
- `src/strategy/domain/domain_service/execution`
- `config/domain_service/execution`
- `tests/strategy/domain/domain_service/test_execution_config_properties.py`
- `tests/strategy/domain/domain_service/test_execution_coordinator_properties.py`
- `tests/strategy/domain/domain_service/test_execution_integration.py`
- Common commands:
  - `python -m src.cli.app run --config config/strategy_config.toml --paper`
- Agent notes:
  - Use when: the task changes smart order execution, scheduling, or execution control details.
  - Read first: src/strategy/domain/domain_service/execution and config/domain_service/execution.
  - Common mistake: do not add facade or coordinator layers here; edit the concrete execution service directly.

### `hedging`

- Depends on: `kernel`, `risk`, `execution`
- Config keys: `service_activation.delta_hedging`, `service_activation.vega_hedging`, `hedging`
- Owned paths:
- `src/strategy/domain/domain_service/hedging`
- `config/strategy_config.toml`
- `tests/strategy/domain/domain_service/test_delta_hedging_service.py`
- `tests/strategy/domain/domain_service/test_vega_hedging_service.py`
- Common commands:
  - `python -m src.cli.app run --config config/strategy_config.toml --paper`
- Agent notes:
  - Use when: the task changes Delta hedging, Vega hedging, or hedging thresholds.
  - Read first: src/strategy/domain/domain_service/hedging and the hedging section in config/strategy_config.toml.
  - Common mistake: do not scatter hedging thresholds through business code; keep them in config-driven hedging services.

### `monitoring`

- Depends on: `kernel`
- Config keys: `service_activation.monitoring`, `service_activation.decision_observability`, `observability`
- Owned paths:
- `src/strategy/infrastructure/monitoring`
- `src/strategy/infrastructure/persistence`
- `tests/strategy/infrastructure/monitoring`
- `tests/strategy/infrastructure/persistence`
- Common commands:
  - `python -m src.cli.app run --config config/strategy_config.toml --paper`
- Agent notes:
  - Use when: the task changes monitoring, snapshots, persistence, or observability output.
  - Read first: src/strategy/infrastructure/monitoring and src/strategy/infrastructure/persistence.
  - Common mistake: do not push monitoring or storage details into domain services; keep them in infrastructure.

### `web`

- Depends on: `kernel`, `monitoring`
- Config keys: `runtime.log_dir`
- Owned paths:
- `src/web`
- `tests/web`
- Common commands:
  - `python src/web/app.py`
- Agent notes:
  - Use when: the task changes the monitoring UI, state readers, or frontend presentation.
  - Read first: src/web and tests/web.
  - Common mistake: do not move strategy decision logic into the web layer; web should stay read-only and presentational.

### `deploy`

- Depends on: `kernel`, `monitoring`, `web`
- Config keys: none
- Owned paths:
- `.dockerignore`
- `.env.example`
- `deploy`
- Common commands:
  - `docker compose --env-file deploy/.env -f deploy/docker-compose.yml up -d --build`
- Agent notes:
  - Use when: the task changes container setup, database integration, or multi-service startup.
  - Read first: deploy/docker-compose.yml, deploy/.env.example, and deploy/Dockerfile.
  - Common mistake: do not start with deploy changes for local strategy iteration; confirm the runtime path and focus assets first.

### `backtest`

- Depends on: `kernel`, `selection`
- Config keys: `strategies`, `service_activation`
- Owned paths:
- `src/backtesting`
- `tests/backtesting`
- Common commands:
  - `python -m src.cli.app backtest --config config/strategy_config.toml --start 2025-01-01 --end 2025-03-01 --no-chart`
- Agent notes:
  - Use when: the task needs execution evidence for strategy logic, contract discovery, or parameter effects.
  - Read first: src/backtesting and tests/backtesting.
  - Common mistake: do not duplicate strategy logic just for backtest; reuse the main strategy contract and config.
