# TASK BRIEF

## Summary

- Agent-first strategy workspace for developing and iterating option strategies.
- Current trading target: `option-universe`
- Current run mode: `standalone`
- Default rule: stay inside the editable surface unless there is a concrete reason to expand scope.

## Recommended Edit Entrypoints

- `src/strategy/strategy_entry.py`
- `src/strategy/application`
- `src/strategy/domain`
- `config/strategy_config.toml`
- `config/general/trading_target.toml`
- `config/domain_service`

## Do Not Edit

- `.codex`
- `.git`
- `.venv`
- `.pytest_cache`
- `.hypothesis`
- `temp`
- `LICENSE`

## Acceptance

- Summary: Agent-first strategy workspace for developing and iterating option strategies.
- Minimal verification command: `python -m src.cli.app focus test`
- Focus navigation files are refreshed and point to the current manifest.
- Validation command succeeds for the current strategy configuration.
- Focus smoke tests pass for the current strategy.

## Key Logs And Outputs

### Key Logs

- `Validation passed`
- `Doctor completed`
- `Focus assets refreshed`

### Key Outputs

- `.focus/SYSTEM_MAP.md`
- `.focus/ACTIVE_SURFACE.md`
- `.focus/TASK_BRIEF.md`
- `.focus/COMMANDS.md`
- `.focus/TASK_ROUTER.md`
- `.focus/TEST_MATRIX.md`
- `.focus/context.json`
