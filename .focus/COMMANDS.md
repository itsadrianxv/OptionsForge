# COMMANDS

## Focus Commands

- `python -m src.cli.app forge`
- `python -m src.cli.app focus show`
- `python -m src.cli.app focus refresh`
- `python -m src.cli.app focus test`
- `python -m src.cli.app focus test --full`

## Verification Modes

- `smoke`: excludes test nodes with `property` or `pbt` in the name.
- `full`: runs the complete runnable selector set for the current focus.

## Current Strategy Commands

- `python -m src.cli.app validate --config config/strategy_config.toml`
- `python -m src.cli.app run --config config/strategy_config.toml --paper`
- `python -m src.cli.app backtest --config config/strategy_config.toml --start 2025-01-01 --end 2025-03-01 --no-chart`
- `python src/web/app.py`
- `python -m src.cli.app focus test`
- `docker compose --env-file deploy/.env -f deploy/docker-compose.yml up -d --build`
