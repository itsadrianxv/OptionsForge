# TEST MATRIX

## Smoke

- 命令: `option-scaffold focus test`
- 说明: 与 Full 使用同一组 selectors，但额外应用节点级过滤。
- 选择器:
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
- 节点过滤:
  - 排除名称包含 `property` 的测试节点。
  - 排除名称包含 `pbt` 的测试节点。

## Full

- 命令: `option-scaffold focus test --full`
- 选择器:
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

## Skipped Packs

- `backtest`: 缺少依赖 `chinese_calendar`
