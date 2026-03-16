# Architecture Patterns

## TOC

- Core layers
- Responsibility map
- Change routing guide
- Working rules

## Core layers

Use these layers as a reference model. Adapt names to the target repository instead of forcing one directory layout.

- Orchestration layer
  - Own workflow sequencing, event dispatch, retries, and side effects.
  - Good names: application, workflow, pipeline, service-layer, use-cases.
- Domain services
  - Own selection, signal, pricing, risk, execution, hedging, and combination logic.
  - Keep business rules close to the domain, not in adapters.
- Domain objects
  - Hold normalized contracts, chains, positions, orders, snapshots, value objects, and events.
  - Keep them explicit and small enough to test in isolation.
- Infrastructure adapters
  - Own broker APIs, market data clients, serializers, repositories, monitoring projections, and external integrations.
  - Translate raw payloads into stable internal contracts.
- Testing surface
  - Mirror the same subsystem boundaries in tests so failures stay localized.

## Responsibility map

- Selection
  - Discover candidate contracts, filter liquidity, score candidates, validate spread structures.
- Signal
  - Turn prepared analytics into open, close, roll, or hedge decisions.
- Pricing
  - Compute theoretical values, implied volatility, greeks, and surface inputs.
- Risk
  - Compute exposure, sizing, concentration, liquidity limits, stop logic, and hedge budgets.
- Execution
  - Turn target actions into order instructions, slicing plans, replace or cancel rules, and status transitions.
- Hedging
  - Manage delta, gamma, vega, or portfolio overlay adjustments.
- Persistence
  - Store snapshots, event history, and replay inputs without owning domain decisions.
- Monitoring
  - Publish read-optimized projections for operators without becoming restart state.
- Gateway adapter
  - Normalize vendor or broker payloads and keep transport logic isolated from strategy rules.

## Change routing guide

- New liquidity, moneyness, expiry, or spread filter
  - Start in the selection service.
  - Update configuration or scoring objects at the same time.
- New entry, exit, roll, or hedge trigger
  - Start in the signal service.
  - Keep orchestration and gateway code unchanged unless the output contract changes.
- New pricing model, IV solver, or greek calculation
  - Start in the pricing subsystem.
  - Keep the gateway layer unaware of pricing internals.
- New exposure control, sizing rule, or hedge budget
  - Start in the risk or hedging subsystem.
- New broker callback mapping or market data normalization rule
  - Start in the gateway adapter.
  - Add normalization tests before touching domain services.
- New restart field, snapshot shape, or replay input
  - Start in persistence contracts and serializers.
  - Update state versioning or migration assumptions together.
- New operator dashboard or monitoring projection
  - Start in monitoring adapters, not restart persistence.

## Working rules

- Build from the domain outward, not from the broker inward.
- Keep signal generation side-effect free.
- Keep adapter code thin and deterministic.
- Keep monitoring projections separate from restart state.
- Prefer explicit data contracts over anonymous dictionaries once a shape stabilizes.
- Avoid umbrella utility modules for core trading rules.
