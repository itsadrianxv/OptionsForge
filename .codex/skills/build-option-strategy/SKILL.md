---
name: build-option-strategy
description: Build or refactor option trading strategy capabilities for OptionForge, including database schema design, market and trade data persistence, vn.py gateway integration, contract processing and filtering, pricing and greeks context, and signal generation. Use when Codex needs to model option chains or contracts, add quote or trade storage, connect gateways, implement selection or signal services, or wire strategy workflows and tests for option strategies.
---

# Build Option Strategy

Use this skill to implement option-strategy changes in OptionForge without losing the repository's layering. Start from domain language and event flow, then wire persistence and gateways, then finish with focused tests.

## Quick Start

1. Read `strategy_spec.toml`, `AGENTS_FOCUS.md`, and `.focus/context.json` when the task changes strategy behavior or editable scope.
2. Route the request to the existing layer before writing code.
   - Workflow orchestration: `src/strategy/application/`
   - Domain rules and data contracts: `src/strategy/domain/`
   - Gateways, persistence, monitoring, subscription: `src/strategy/infrastructure/`
3. Load references on demand.
   - Read [repo-map.md](references/repo-map.md) to choose edit locations and test files.
   - Read [schema-and-persistence.md](references/schema-and-persistence.md) to design tables, replay inputs, and persistence boundaries.
4. Change interfaces or schemas directly when that makes the model simpler. This project is not deployed; do not spend time on backward-compatibility shims.
5. Let application workflows compose concrete services directly. Do not add new facade or coordinator layers in domain or infrastructure code.

## Workflow

### Scope the change

- Pin down the strategy style first: directional, volatility, spread, income, hedging, or portfolio management.
- Pin down the event clock: tick, quote, bar, timer, order callback, trade callback, or restart recovery.
- Pin down the venue contract: which gateway provides market data, which gateway accepts orders, and which IDs must survive reconnects.
- Decide whether the task changes raw market facts, derived analytics, execution state, or warm-restart state.

### Place logic in the correct layer

- Put contract-universe construction, liquidity filters, moneyness filters, expiry filters, and ranking under `domain_service/selection/`.
- Put open, close, roll, and hedge decisions under `domain_service/signal/`. Return structured signal decisions; do not place orders here.
- Put pricing, IV, greeks, and volatility-surface work under `domain_service/pricing/`.
- Put sizing, concentration, liquidity, stop, and decay rules under `domain_service/risk/`.
- Put order slicing, scheduling, and execution instructions under `domain_service/execution/`.
- Put delta, gamma, and vega hedge rules under `domain_service/hedging/`.
- Keep `infrastructure/gateway/` thin. Normalize vn.py payloads, request mapping, status mapping, and reconnect behavior there.
- Keep `infrastructure/persistence/` focused on state snapshots and replay inputs. Monitoring snapshots belong under `infrastructure/monitoring/`.

### Build from the domain outward

- Prefer extending existing value objects and entities before inventing new shapes.
- Reuse the current signal contract when possible: `SignalContext`, `SignalDecision`, `OptionSelectionPreference`, and `DecisionTrace`.
- Make identifiers explicit: `vt_symbol`, `gateway_name`, `exchange`, `underlying_symbol`, `expiry`, `strike`, `option_type`, `trading_day`, and event timestamps.
- Separate raw gateway payloads from derived analytics and from strategy state.
- Persist enough rationale to explain why selection or signal logic fired.

### Handle contract selection and combinations

- Separate candidate generation from final trading decisions.
- Filter liquidity before scoring.
- Keep thresholds and ranking weights in config or value-object modules, not as magic numbers in workflows.
- Validate multi-leg structures against combination rules before signal generation or order creation.
- Keep combination lifecycle and PnL logic in the combination services instead of duplicating leg math in signal code.

### Handle gateways and execution

- Extend the smallest specific adapter under `src/strategy/infrastructure/gateway/`.
- Normalize statuses and IDs immediately after crossing the gateway boundary.
- Preserve broker order refs, trade IDs, and raw payload fragments required for audit or reconciliation.
- Treat reconnects, duplicate callbacks, and partial fills as normal operating conditions.

### Handle persistence and replay

- Model read patterns first: warm restart, backtest replay, monitoring queries, and post-trade analysis.
- Use append-only records for market and execution events when replay or audit matters.
- Keep fast-recovery snapshots separate from long-form event history.
- Read `src/strategy/infrastructure/persistence/README.md` before changing persistence boundaries.
- When changing restart state, version the snapshot shape intentionally and update tests together.

### Handle signal generation

- Build signals from prepared indicators and context, not directly from gateway I/O.
- Return structured `SignalDecision` values with `action`, `signal_name`, `rationale`, `confidence`, selection preference, close target, and metadata when available.
- Keep entry and exit logic symmetric. Define unwind or roll conditions together with entry conditions.
- Record decision traces when the workflow needs explainability or post-mortem analysis.

### Verify the change

- Add unit tests as close as possible to the changed module.
- Add persistence round-trip or replay tests when schemas or state loading change.
- Add gateway normalization tests when request or callback mapping changes.
- Run focused tests first, then wider validation or backtest commands if the change affects the main strategy flow.

## Repo Pointers

- Application entry points live in `src/strategy/application/`.
- Existing option-centric services live in `src/strategy/domain/domain_service/selection`, `signal`, `pricing`, `risk`, `execution`, `hedging`, and `combination`.
- Existing signal contracts live in `src/strategy/domain/value_object/signal/strategy_contract.py`.
- Existing persistence boundaries live in `src/strategy/infrastructure/persistence/`.
- Existing gateway adapters live in `src/strategy/infrastructure/gateway/`.
- Test layout mirrors source layout under `tests/strategy/`.

## Typical Tasks

- Add a database schema for option contracts, chains, quotes, greeks, orders, trades, and restart snapshots.
- Persist quote, order, and trade events while keeping selection and signal services pure.
- Connect a new vn.py gateway or normalize a missing callback or status mapping.
- Implement contract filtering for liquidity, expiry, delta, skew, spread structure, or ranking.
- Add open, close, roll, or hedge signal logic and the tests that prove it.

## References

- Use [repo-map.md](references/repo-map.md) for file-placement and testing guidance.
- Use [schema-and-persistence.md](references/schema-and-persistence.md) for table design, replay boundaries, and anti-patterns.
