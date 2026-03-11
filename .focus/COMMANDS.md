# COMMANDS

## Focus Commands

- `option-scaffold focus show`
- `option-scaffold focus refresh`
- `option-scaffold focus test`
- `option-scaffold focus test --full`

## Test Modes

- `smoke`：默认排除名称包含 `property` / `pbt` 的测试节点。
- `full`：运行当前焦点的完整 runnable selectors。

## Current Strategy Commands

- `option-scaffold validate --config config/strategy_config.toml`
- `option-scaffold run --config config/strategy_config.toml --paper`
- `option-scaffold backtest --config config/strategy_config.toml --start 2025-01-01 --end 2025-03-01 --no-chart`
- `python src/web/app.py`
- `option-scaffold focus test`
- `docker compose --env-file deploy/.env -f deploy/docker-compose.yml up -d --build`
