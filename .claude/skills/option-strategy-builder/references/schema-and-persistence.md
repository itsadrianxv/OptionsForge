# Schema and Persistence

## TOC

- Modeling principles
- Stable identifiers
- Suggested storage slices
- Replay and restart
- Gateway and execution persistence
- Anti-patterns

## Modeling principles

- Model read paths first.
  - Live trading needs low-latency access to current state.
  - Warm restart needs compact and trustworthy recovery data.
  - Replay needs append-only historical facts.
  - Monitoring needs read-optimized projections.
  - Analytics needs causal links across decisions and fills.
- Separate static contract metadata, market facts, derived analytics, execution facts, and restart snapshots.
- Keep exchange time, broker time, ingest time, and processing time distinct when the source provides them.
- Preserve raw payload fragments when upstream mappings are unstable or regulated workflows require auditability.
- Persist expensive or audit-critical derived analytics; recompute cheap deterministic values during replay.
- Use snapshots for recovery, not as a substitute for event history.

## Stable identifiers

Use stable identifiers consistently across schemas, normalized objects, and logs:

- strategy_name
- gateway_name
- exchange
- underlying_symbol
- venue_symbol
- option_type
- strike
- expiry
- multiplier
- trading_day
- event_time
- ingest_time
- order_ref
- broker_order_id
- trade_id
- position_key
- trace_id

Do not treat a naked symbol string as enough identity for an option contract when expiry, strike, option type, or venue can change meaning.

## Suggested storage slices

Use these as design slices, not mandatory table names.

- Contract master
  - Store listed option metadata and lifecycle state.
  - Example fields: symbol identity, underlying, strike, expiry, option type, multiplier, tick size, listed_at, delisted_at, status, raw_payload.
- Chain snapshots
  - Store point-in-time contract universe views for an underlying and expiry set.
  - Example fields: underlying, snapshot_time, atm_reference, expiry_set, contracts_payload.
- Market quotes or ticks
  - Store append-only top-of-book or depth events.
  - Example fields: symbol identity, bid and ask prices, bid and ask volumes, last price, volume, open interest, depth payload, raw_payload.
- Bar history
  - Store replay and indicator warmup inputs.
  - Example fields: symbol identity, interval, bar_time, OHLCV, turnover, open_interest.
- Pricing snapshots
  - Store theoretical values, IV, greeks, and model metadata when these outputs matter beyond the current tick.
- Volatility surface snapshots
  - Store fitted surface parameters or dense surface points when they affect selection, risk, or replay.
- Selection runs
  - Store which candidates were considered, how they were scored, and which ones were selected.
- Signal events
  - Store structured open, close, roll, or hedge decisions with rationale and confidence.
- Orders and trades
  - Store order lifecycle and fills with both internal and broker identifiers.
- Position snapshots
  - Store current exposure and relevant valuation context for recovery and analytics.
- Strategy-state snapshots
  - Store compact restart state with an explicit schema version.

## Replay and restart

- Capture the minimum state needed to resume safely:
  - recent bars for indicator warmup
  - current contract universe for tracked underlyings
  - working orders and open positions
  - latest relevant decision context when exits depend on prior reasoning
  - strategy parameters or config version used to build current state
- Use full replay when correctness depends on the whole event path.
- Use snapshots when startup speed matters more and the snapshot is trustworthy.
- Keep snapshot contents versioned.
- Treat replay inputs, restart state, and monitoring projections as separate concerns.

## Gateway and execution persistence

- Normalize broker and vendor payloads before they reach repositories used by the rest of the system.
- Preserve both internal IDs and external IDs.
- Keep the causal chain visible:
  - contract discovery
  - selection result
  - signal decision
  - order instruction
  - order lifecycle
  - trade fill
  - position update
- Deduplicate duplicate callbacks using stable keys such as gateway name, external ID, event time, and status.
- Model partial fills, replace flows, and cancels explicitly when execution logic depends on them.

## Anti-patterns

- One giant JSON blob for market data, signals, orders, and positions.
- Signal logic that reads directly from databases or writes directly to broker APIs.
- Monitoring tables used as restart persistence.
- Contract identity that omits exchange, expiry, strike, or option type.
- Derived analytics stored without the market timestamp they depend on.
- Broker adapters that contain pricing, signal, or risk decisions.
