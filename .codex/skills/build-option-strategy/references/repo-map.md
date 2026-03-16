# Repo Map

## TOC

- Application workflows
- Domain services
- Domain data contracts
- Infrastructure adapters
- Testing map
- Change routing cheat sheet

## Application workflows

- `src/strategy/application/event_bridge.py`
  - Bridge inbound events into workflow calls.
- `src/strategy/application/market_workflow.py`
  - Orchestrate the market-data-driven path from prepared inputs to domain decisions.
- `src/strategy/application/subscription_workflow.py`
  - Manage contract-universe discovery and subscriptions.
- `src/strategy/application/state_workflow.py`
  - Load, save, and restore strategy state.
- `src/strategy/application/lifecycle_workflow.py`
  - Handle startup, shutdown, and recovery coordination.

## Domain services

- `src/strategy/domain/domain_service/selection/option_selector_service.py`
  - Filter contracts by liquidity, moneyness, expiry, and score.
- `src/strategy/domain/domain_service/signal/signal_service.py`
  - Produce open and close decisions. Keep it side-effect free.
- `src/strategy/domain/domain_service/pricing/`
  - Pricing engine, IV solver, greeks, and volatility-surface logic.
- `src/strategy/domain/domain_service/risk/`
  - Sizing, concentration, liquidity, stop-loss, decay, and portfolio risk.
- `src/strategy/domain/domain_service/execution/`
  - Order scheduling and execution-instruction generation.
- `src/strategy/domain/domain_service/hedging/`
  - Delta, gamma, and vega hedge logic.
- `src/strategy/domain/domain_service/combination/`
  - Multi-leg recognition, lifecycle, PnL, greeks, and combination risk.

## Domain data contracts

- `src/strategy/domain/entity/target_instrument.py`
  - Hold bars plus computed indicators for a tradable target.
- `src/strategy/domain/entity/position.py`
  - Hold live position state.
- `src/strategy/domain/entity/order.py`
  - Hold order state.
- `src/strategy/domain/entity/combination.py`
  - Hold multi-leg combination state.
- `src/strategy/domain/value_object/market/`
  - Normalize contracts, chains, snapshots, and quote requests.
- `src/strategy/domain/value_object/pricing/`
  - Hold pricing, greeks, and volatility-surface values.
- `src/strategy/domain/value_object/selection/`
  - Hold selection config and scored results.
- `src/strategy/domain/value_object/signal/strategy_contract.py`
  - Define `SignalContext`, `SignalDecision`, `OptionSelectionPreference`, and `DecisionTrace`.
- `src/strategy/domain/event/`
  - Hold event types and risk-event definitions.

## Infrastructure adapters

- `src/strategy/infrastructure/gateway/vnpy_connection_gateway.py`
  - Connection and session handling.
- `src/strategy/infrastructure/gateway/vnpy_market_data_gateway.py`
  - Market-data access and mapping.
- `src/strategy/infrastructure/gateway/vnpy_quote_gateway.py`
  - Quote-request integration.
- `src/strategy/infrastructure/gateway/vnpy_order_gateway.py`
  - Order submission and cancellation mapping.
- `src/strategy/infrastructure/gateway/vnpy_trade_execution_gateway.py`
  - Trade-execution-specific mapping.
- `src/strategy/infrastructure/gateway/vnpy_account_gateway.py`
  - Account snapshot integration.
- `src/strategy/infrastructure/gateway/vnpy_event_gateway.py`
  - vn.py event-engine integration.
- `src/strategy/infrastructure/gateway/vnpy_gateway_adapter.py`
  - Shared adapter utilities.
- `src/strategy/infrastructure/persistence/README.md`
  - State the persistence boundary. Read it before moving code across modules.
- `src/strategy/infrastructure/persistence/state_repository.py`
  - Append and restore strategy-state snapshots.
- `src/strategy/infrastructure/persistence/history_data_repository.py`
  - Warm up and replay historical bars.
- `src/strategy/infrastructure/persistence/auto_save_service.py`
  - Trigger periodic saves.
- `src/strategy/infrastructure/persistence/model/strategy_state_po.py`
  - Persistence object for strategy-state snapshots.
- `src/strategy/infrastructure/monitoring/strategy_monitor.py`
  - Monitoring output only. Do not treat it as restart persistence.
- `src/strategy/infrastructure/monitoring/model/monitor_signal_event_po.py`
  - Monitoring event model.
- `src/strategy/infrastructure/monitoring/model/monitor_signal_snapshot_po.py`
  - Monitoring snapshot model.

## Testing map

- `tests/strategy/application/`
  - Workflow orchestration tests.
- `tests/strategy/domain/domain_service/`
  - Most domain-service tests.
- `tests/strategy/domain/domain_service/test_option_selector_*.py`
  - Existing selection and scoring test patterns.
- `tests/strategy/domain/domain_service/test_pricing_*.py`
  - Existing pricing-engine test patterns.
- `tests/strategy/domain/domain_service/test_*hedging*.py`
  - Existing hedging test patterns.
- `tests/strategy/infrastructure/persistence/`
  - Snapshot and replay tests.
- `tests/strategy/infrastructure/monitoring/`
  - Monitoring-only persistence tests.
- `tests/backtesting/test_option_discovery.py`
  - Option-discovery and contract-universe behavior.

## Change routing cheat sheet

- New liquidity or expiry filter
  - Start in `selection/option_selector_service.py`
  - Also check selection config value objects and selector tests
- New open, close, roll, or hedge signal rule
  - Start in `signal/signal_service.py`
  - Also check signal contracts, market workflow, and domain tests
- New pricing, IV, greek, or surface feature
  - Start in `pricing/`
  - Also check pricing value objects and pricing tests
- New hedge budget or exposure rule
  - Start in `hedging/` or `risk/`
  - Also check portfolio aggregation tests
- New order mapping or broker callback normalization
  - Start in `infrastructure/gateway/`
  - Also check execution services and infrastructure tests
- New restart field or persistence structure
  - Start in `infrastructure/persistence/`
  - Also check serializer, persistence objects, and replay tests
- New monitoring-only projection
  - Start in `infrastructure/monitoring/`
  - Do not move monitoring models into `infrastructure/persistence/`

## Working rules

- Compose concrete services from application workflows. Do not add new facade or coordinator layers for domain or infrastructure code.
- Keep vendor payload translation inside gateway adapters.
- Keep signal services pure. Let workflows call gateways and persistence after domain decisions are made.
- Create new modules beside close peers when no exact file exists. Avoid umbrella utility modules for domain logic.
