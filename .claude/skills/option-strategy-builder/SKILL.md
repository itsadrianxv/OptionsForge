---
name: option-strategy-builder
description: Design or implement option trading strategy systems, including schema modeling, market and trade persistence, gateway integration, contract processing and filtering, pricing and greeks workflows, signal generation, risk, execution, hedging, and replay or monitoring flows. Use when an agent needs a reusable workflow for building option strategy software across broker APIs, data vendors, and codebases.
---

# Option Strategy Builder

Use this skill to design or implement an option trading strategy system in a platform-neutral way. Focus on domain clarity first, then data flow, then broker or market integration, then testing.

## Quick Start

1. Clarify the strategy objective before writing code.
   - What is the edge: directional, volatility, carry, spread, hedging, market making, or portfolio overlay?
   - What is the operating clock: tick, quote, bar, timer, order callback, trade callback, or restart recovery?
   - What is the venue model: broker API, market data vendor, simulation engine, or multiple sources?
2. Load references only when they are needed.
   - Read [architecture-patterns.md](references/architecture-patterns.md) to choose service boundaries and module placement.
   - Read [schema-and-persistence.md](references/schema-and-persistence.md) to design storage, replay, and audit flows.
   - Read [example-optionforge.md](references/example-optionforge.md) only if you need a concrete repository mapping example.
3. Keep the implementation generic until the repository or API proves otherwise. Do not assume a specific framework, broker, or event engine.

## Workflow

### Frame the trading problem

- Define the traded universe: single options, option chains, structured spreads, or option plus underlying hedges.
- Define the decision horizon: intraday, swing, expiry-cycle, or continuous hedging.
- Define what must be persisted for correctness, recovery, monitoring, and post-trade analysis.
- Define which outputs the strategy must produce: signals, quotes, orders, hedges, risk alerts, or monitoring events.

### Model the domain

- Separate candidate discovery from trade decisions.
- Treat contract selection, pricing, signal generation, risk, execution, and hedging as distinct responsibilities.
- Keep raw venue payloads separate from normalized domain objects.
- Make identifiers explicit: symbol, exchange, option type, strike, expiry, multiplier, trading day, timestamps, broker order ID, trade ID, and position key.
- Prefer small value objects and entities over one large mutable state blob.

### Design the data model

- Model read paths first: live trading, warm restart, replay, monitoring, and post-trade analytics.
- Separate static contract metadata, market facts, derived analytics, execution facts, and restart snapshots.
- Use append-only event storage when auditability or replay matters.
- Use snapshots only for fast recovery or read-optimized projections.
- Version persisted state intentionally when strategy behavior depends on it.

### Define the gateway boundary

- Keep gateway adapters thin and deterministic.
- Normalize market data, order status, trade events, and account state as soon as they cross the boundary.
- Preserve raw payload fragments when vendor mappings are unstable or audit requirements are high.
- Handle reconnects, duplicate callbacks, and partial fills as normal conditions, not edge cases.
- Do not put selection, signal, or risk logic inside broker adapters.

### Build the contract universe

- Start with discovery rules: underlying, expiry windows, strike bands, moneyness, liquidity, open interest, and spread quality.
- Filter contracts before scoring them.
- Score candidates with explicit configuration, not hidden constants.
- Validate multi-leg structures before turning them into executable instructions.
- Keep combination recognition and lifecycle logic in dedicated services instead of duplicating leg math across the system.

### Build the signal pipeline

- Build indicators and derived analytics before generating signals.
- Generate structured decisions, not plain strings, whenever the codebase supports it.
- Carry rationale, confidence, and selection preferences through the pipeline when they affect execution or explainability.
- Define entry, exit, unwind, roll, and hedge conditions together so lifecycle logic stays symmetric.
- Keep signal code side-effect free; let orchestration or application layers call gateways and persistence afterward.

### Build execution and risk

- Separate target exposure from execution instructions.
- Keep sizing, concentration, liquidity, stop logic, and hedge budgeting in dedicated risk services.
- Model partial fills, replace or cancel flows, and stale orders explicitly.
- Preserve the causal chain from selection to signal to order to fill to position update.
- Avoid adding facade or coordinator layers unless the repository already relies on them.

### Build persistence and replay

- Persist the minimum state needed for safe restart.
- Persist the full event trail when replay, audit, or analytics require it.
- Keep monitoring projections separate from restart state.
- Store enough context to reproduce why a signal or hedge fired.
- If replay inputs are cheap to recompute, prefer recomputation over storing every derived field.

### Verify the implementation

- Add focused tests for selection, pricing, signal, risk, execution, and persistence boundaries.
- Add round-trip tests for persisted state and normalization tests for gateway payloads.
- Add replay tests when warm restart or historical rebuild correctness matters.
- Smoke test at least three scenarios: schema design, contract filtering, and signal generation.
- Validate that the workflow still works for a different venue or broker than the first example.

## Output Expectations

- Produce clear domain boundaries before implementation details.
- Prefer repository-neutral naming unless the target codebase already defines names.
- State assumptions about broker APIs, timestamps, fill semantics, and persistence guarantees.
- Keep examples short and reusable across frameworks.

## Typical Tasks

- Design schemas for option contracts, chains, quotes, greeks, orders, trades, and restart snapshots.
- Add market and trade persistence without mixing domain logic into repository or adapter code.
- Connect a new broker or market data gateway with normalized event mapping.
- Implement contract filters for liquidity, expiry, delta, skew, or spread structure.
- Add signal logic for entry, exit, roll, hedge, or volatility regime changes.

## References

- Use [architecture-patterns.md](references/architecture-patterns.md) for common module boundaries.
- Use [schema-and-persistence.md](references/schema-and-persistence.md) for storage and replay design.
- Use [example-optionforge.md](references/example-optionforge.md) only as an optional mapping example.
