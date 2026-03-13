# TEST MATRIX

## Smoke

- Command: `python -m src.cli.app focus test`
- Notes: smoke uses the same selectors as full mode, plus keyword filters.
- Selectors:
  - `tests/main/focus`
  - `tests/cli/test_app.py`
  - `tests/strategy/application/test_market_workflow_pipeline.py`
  - `tests/strategy/infrastructure/bar_pipeline/test_bar_pipeline.py`
  - `tests/strategy/infrastructure/subscription/test_subscription_mode_engine.py`
  - `tests/strategy/infrastructure/utils/test_date_calculator.py`
  - `tests/strategy/domain/domain_service/test_selection_integration.py`
  - `tests/strategy/domain/domain_service/test_pricing_engine.py`
  - `tests/strategy/domain/domain_service/risk/test_risk_integration.py`
  - `tests/strategy/domain/domain_service/combination/test_combination_integration.py`
  - `tests/strategy/domain/domain_service/test_execution_integration.py`
  - `tests/strategy/domain/domain_service/test_delta_hedging_service.py`
  - `tests/strategy/domain/domain_service/test_vega_hedging_service.py`
  - `tests/strategy/infrastructure/monitoring/test_strategy_monitor_serialization.py`
  - `tests/strategy/infrastructure/persistence/test_state_repository.py`
  - `tests/web/test_monitor_template.py`
  - `tests/web/test_strategy_state_reader.py`
  - `tests/backtesting/test_cli.py`
  - `tests/backtesting/test_runner.py`
- Keyword filters:
  - Exclude test nodes whose names contain `property`.
  - Exclude test nodes whose names contain `pbt`.

## Full

- Command: `python -m src.cli.app focus test --full`
- Selectors:
  - `tests/main/focus`
  - `tests/cli/test_app.py`
  - `tests/strategy/application/test_market_workflow_pipeline.py`
  - `tests/strategy/infrastructure/bar_pipeline/test_bar_pipeline.py`
  - `tests/strategy/infrastructure/subscription/test_subscription_mode_engine.py`
  - `tests/strategy/infrastructure/utils/test_date_calculator.py`
  - `tests/strategy/domain/domain_service/test_selection_integration.py`
  - `tests/strategy/domain/domain_service/test_pricing_engine.py`
  - `tests/strategy/domain/domain_service/risk/test_risk_integration.py`
  - `tests/strategy/domain/domain_service/combination/test_combination_integration.py`
  - `tests/strategy/domain/domain_service/test_execution_integration.py`
  - `tests/strategy/domain/domain_service/test_delta_hedging_service.py`
  - `tests/strategy/domain/domain_service/test_vega_hedging_service.py`
  - `tests/strategy/infrastructure/monitoring/test_strategy_monitor_serialization.py`
  - `tests/strategy/infrastructure/persistence/test_state_repository.py`
  - `tests/web/test_monitor_template.py`
  - `tests/web/test_strategy_state_reader.py`
  - `tests/backtesting/test_cli.py`
  - `tests/backtesting/test_runner.py`

## Skipped Packs

- none
