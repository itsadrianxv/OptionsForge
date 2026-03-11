# TEST.md

## Test Plan

- Strategy: `main`
- Summary: AI-first scaffold workspace for developing and iterating option strategies.
- Preset: `custom`
- Focus Packs: `kernel`, `selection`, `pricing`, `risk`, `execution`, `hedging`, `monitoring`, `web`, `deploy`, `backtest`

### Completion Checks

- Focus navigation files are refreshed and point to the current manifest.
- Validation command succeeds for the current strategy configuration.
- Focus smoke tests pass for the current strategy.

### Scenarios

- Validate generated contracts and strategy imports.
- Validate configuration and focus navigation assets.
- Run focus smoke tests for enabled packs.

### Strategy Logic Notes

#### Entry Rules

- Define the minimum market state needed before opening a position.
- Describe the signal threshold or pattern that triggers entry.

#### Exit Rules

- Describe profit-taking and stop-loss conditions.
- State when positions must be flattened before expiry or session close.

#### Selection Rules

- Describe how the underlying and option chain are chosen.
- Explain strike, expiry, and option type preferences.

#### Sizing Rules

- Define the maximum position count and per-trade capital usage.

#### Risk Rules

- State hard limits for margin, Greeks, or portfolio concentration.

#### Hedging Rules

- Describe whether Delta or Vega hedging is enabled and when it should trigger.

#### Observability Notes

- List the key decisions and signals that must appear in logs or monitoring.

## Latest Results

- validate: passed with 0 errors and 0 warnings
- focus test: passed with exit code 0
