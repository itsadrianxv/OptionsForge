from __future__ import annotations

from types import SimpleNamespace

import pytest

from src.strategy.runtime.registry import CAPABILITY_REGISTRY
from src.strategy.runtime.builder import StrategyRuntimeBuilder


def _entry() -> SimpleNamespace:
    return SimpleNamespace(logger=SimpleNamespace(info=lambda *a, **k: None))


def _manifest(**overrides: bool) -> dict[str, bool]:
    manifest = {key: False for key in CAPABILITY_REGISTRY}
    manifest.update(overrides)
    return manifest


def test_builder_rejects_unknown_capability() -> None:
    with pytest.raises(ValueError, match="unknown capability"):
        StrategyRuntimeBuilder().build(
            _entry(),
            {"service_activation": {"unknown_capability": True}},
        )


def test_builder_rejects_missing_manifest_keys() -> None:
    with pytest.raises(ValueError, match="missing capability keys"):
        StrategyRuntimeBuilder().build(
            _entry(),
            {"service_activation": {"option_chain": True}},
        )


def test_builder_returns_empty_runtime_for_complete_disabled_manifest() -> None:
    runtime = StrategyRuntimeBuilder().build(
        _entry(),
        {"service_activation": _manifest()},
    )

    assert runtime.enabled_capabilities == ()
    assert runtime.lifecycle.init_hooks == ()
    assert runtime.state.snapshot_sinks == ()


def test_builder_rejects_multiple_rebalance_planners() -> None:
    with pytest.raises(ValueError, match="portfolio.rebalance_planner"):
        StrategyRuntimeBuilder().build(
            _entry(),
            {
                "service_activation": _manifest(
                    greeks_calculator=True,
                    delta_hedging=True,
                    vega_hedging=True,
                )
            },
        )
