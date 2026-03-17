from __future__ import annotations

from types import SimpleNamespace

from src.strategy.runtime.registry import CAPABILITY_REGISTRY


def _manifest(**overrides: bool) -> dict[str, bool]:
    manifest = {key: False for key in CAPABILITY_REGISTRY}
    manifest.update(overrides)
    return manifest


def test_advanced_scheduler_wraps_execution_planner_output() -> None:
    from src.strategy.runtime.providers.advanced_order_scheduler import PROVIDER

    contribution = PROVIDER.build(
        SimpleNamespace(),
        {"service_activation": _manifest(smart_order_executor=True, advanced_order_scheduler=True)},
        SimpleNamespace(),
    )

    assert contribution.open_pipeline.execution_scheduler is not None
