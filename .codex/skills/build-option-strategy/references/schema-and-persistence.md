# Schema and Persistence

## TOC

- Modeling principles
- Stable identifiers
- Suggested storage slices
- Warm restart and replay
- Gateway and execution persistence
- Anti-patterns
- Change checklist

## Modeling principles

- Separate static contract data, market facts, derived analytics, execution facts, and restart snapshots.
- Model read patterns first.
  - Warm restart needs fast point-in-time recovery.
  - Backtest replay needs append-only historical facts.
  - Monitoring needs read-optimized projections.
  - Post-trade analysis needs causal links between signals, orders, trades, and positions.
- Prefer explicit business identifiers over loosely structured payloads.
- Keep event time, exchange time, and ingest time distinct when the source provides them.
- Preserve raw payload fragments when vendor mappings are unstable or audit requirements are high.
- Persist expensive or audit-critical derived analytics. Recompute cheap deterministic values during replay.
- Split current-state snapshots from immutable history instead of forcing one table to satisfy every read path.

## Stable identifiers

Use these fields consistently across value objects, persistence models, and gateway mappings:

- `strategy_name`
- `gateway_name`
- `exchange`
- `underlying_symbol`
- `vt_symbol`
- `option_type`
- `strike`
- `expiry`
- `multiplier`
- `trading_day`
- `event_time`
- `ingest_time`
- `order_ref`
- `broker_order_id`
- `trade_id`
- `position_key`
- `trace_id`

Do not rely on a naked symbol string when an option contract also needs exchange, expiry, strike, and option type to stay unique.

## Suggested storage slices

Use these as starting points, not mandatory tables. Match names and schemas to the repository's conventions.

- Contract master
  - Purpose: listed option metadata and lifecycle
  - Typical fields: `vt_symbol`, `gateway_name`, `exchange`, `underlying_symbol`, `option_type`, `strike`, `expiry`, `multiplier`, `price_tick`, `listed_at`, `delisted_at`, `status`, `raw_payload`
- Chain snapshots
  - Purpose: point-in-time contract universe and chain composition
  - Typical fields: `underlying_symbol`, `expiry`, `snapshot_time`, `atm_reference`, `contracts_payload`
- Market quotes or ticks
  - Purpose: append-only top-of-book or depth snapshots
  - Typical fields: `vt_symbol`, `event_time`, `ingest_time`, `bid_price_1`, `ask_price_1`, `bid_volume_1`, `ask_volume_1`, depth payload, `volume`, `open_interest`, `raw_payload`
- Bar history
  - Purpose: replay and indicator warmup
  - Typical fields: `vt_symbol`, `interval`, `bar_time`, `open`, `high`, `low`, `close`, `volume`, `turnover`, `open_interest`
- Pricing snapshots
  - Purpose: theoretical value, IV, greeks, skew inputs
  - Typical fields: `vt_symbol`, `event_time`, `model_name`, `underlying_price`, `theoretical_price`, `iv`, `delta`, `gamma`, `theta`, `vega`, `rho`, `metadata`
- Volatility-surface snapshots
  - Purpose: store fitted surface parameters or dense grid points
  - Typical fields: `underlying_symbol`, `snapshot_time`, `surface_model`, `surface_payload`, `fit_quality`
- Selection runs and candidates
  - Purpose: explain why a contract or combination was chosen
  - Typical fields: `trace_id`, `strategy_name`, `event_time`, `candidate_symbol`, `candidate_payload`, `score`, `rank`, `selected`, `rationale`
- Signal events
  - Purpose: persist `SignalDecision` output and reasoning
  - Typical fields: `trace_id`, `strategy_name`, `event_time`, `action`, `signal_name`, `rationale`, `confidence`, `selection_preference_payload`, `metadata`
- Orders and trades
  - Purpose: audit and reconciliation
  - Typical fields: `strategy_name`, `gateway_name`, `order_ref`, `broker_order_id`, `trade_id`, `status`, `side`, `offset`, `price`, `volume`, `filled_volume`, `event_time`, `raw_payload`
- Position snapshots
  - Purpose: recover live exposure and post-trade state
  - Typical fields: `position_key`, `strategy_name`, `vt_symbol`, `direction`, `volume`, `avg_price`, `greeks_payload`, `snapshot_time`
- Strategy-state snapshots
  - Purpose: fast recovery of working state
  - Typical fields: `strategy_name`, `schema_version`, `saved_at`, `snapshot_json`

## Warm restart and replay

Warm restart usually needs a smaller dataset than full replay. Capture the minimum state required to resume decisions safely:

- Recent bars per active symbol for indicator warmup
- Current contract master or chain mapping for selected underlyings
- Open positions and working orders
- Latest relevant signal or decision trace if exit logic depends on prior context
- Config version or strategy parameters used to build current state
- Optional pricing or surface state when recomputation is expensive relative to startup cost

Use full replay when correctness depends on the full event path. Use snapshots when startup speed matters more and the snapshot can be trusted.

The current repository already has an append-only JSON snapshot pattern in `state_repository.py`. Extend it intentionally:

- Keep snapshot contents versioned
- Update serializer logic together with schema changes
- Decide which fields remain in JSON and which deserve first-class relational tables
- Keep replay inputs separate from monitoring projections

## Gateway and execution persistence

- Normalize broker callbacks into repository-safe states as soon as they cross the gateway boundary.
- Preserve both strategy-side IDs and broker-side IDs.
- Keep the causal chain visible:
  - selection run
  - signal event
  - order instruction
  - order lifecycle
  - trade fill
  - position update
- Deduplicate duplicate callbacks with a stable key such as gateway plus broker ID plus event time plus status.
- Model partial fills and cancels explicitly. Do not collapse order lifecycle into a single terminal row unless the task only needs reporting.

## Anti-patterns

- One giant JSON blob for all market data, all signals, all orders, and all positions
- Signal services reading from the database or placing orders directly
- Monitoring tables mixed into restart persistence modules
- Contract identity modeled without exchange, expiry, strike, and option type
- Derived analytics stored without the market timestamp they were computed from
- Backward-compatibility shims that preserve old schema shapes in a project that is not deployed
- New facade or coordinator layers that hide the real service boundaries

## Change checklist

1. Define the read paths before defining the tables.
2. Pick stable identifiers and timestamp semantics.
3. Decide what must be append-only and what can be snapshotted.
4. Keep monitoring, replay, and restart concerns separated.
5. Update serializers or schema-version handling when state snapshots change.
6. Add tests for round-trip persistence, replay, or status normalization.
7. Keep domain logic out of persistence objects and gateway adapters.
