from __future__ import annotations

from types import SimpleNamespace

from src.strategy.runtime.registry import CAPABILITY_REGISTRY


def _manifest(**overrides: bool) -> dict[str, bool]:
    manifest = {key: False for key in CAPABILITY_REGISTRY}
    manifest.update(overrides)
    return manifest


def test_position_sizing_provider_contributes_close_volume_planner() -> None:
    from src.strategy.runtime.providers.position_sizing import PROVIDER

    contribution = PROVIDER.build(
        SimpleNamespace(
            position_sizing_service=SimpleNamespace(),
            market_gateway=SimpleNamespace(get_tick=lambda vt_symbol: None),
            logger=SimpleNamespace(info=lambda *a, **k: None),
        ),
        {"service_activation": _manifest(position_sizing=True)},
        kernel=SimpleNamespace(),
    )

    assert contribution.close_pipeline.close_volume_planner is not None


def test_portfolio_risk_provider_contributes_open_and_close_risk_roles() -> None:
    from src.strategy.runtime.providers.portfolio_risk import PROVIDER

    contribution = PROVIDER.build(
        SimpleNamespace(
            portfolio_risk_aggregator=SimpleNamespace(),
            risk_thresholds=SimpleNamespace(),
        ),
        {"service_activation": _manifest(portfolio_risk=True, greeks_calculator=True)},
        kernel=SimpleNamespace(),
    )

    assert contribution.open_pipeline.risk_evaluator is not None
    assert contribution.close_pipeline.risk_evaluator is not None


def test_exit_orchestration_provider_contributes_generic_close_roles() -> None:
    from src.strategy.runtime.providers.exit_orchestration import PROVIDER

    contribution = PROVIDER.build(
        SimpleNamespace(
            exit_intent_provider=SimpleNamespace(provide=lambda **kwargs: None),
            exit_group_resolver=SimpleNamespace(resolve=lambda **kwargs: "group-key"),
            exit_freshness_guard=SimpleNamespace(check=lambda **kwargs: None),
        ),
        {"service_activation": _manifest(exit_orchestration=True)},
        kernel=SimpleNamespace(),
    )

    assert contribution.close_pipeline.exit_intent_provider is not None
    assert contribution.close_pipeline.exposure_group_resolver is not None
    assert contribution.close_pipeline.freshness_guard is not None
