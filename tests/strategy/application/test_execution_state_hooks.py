from __future__ import annotations

from datetime import datetime
from types import SimpleNamespace

from src.strategy.application.lifecycle_workflow import LifecycleWorkflow
from src.strategy.application.state_workflow import StateWorkflow
from src.strategy.infrastructure.persistence.state_repository import ArchiveNotFound
from src.strategy.runtime.registry import CAPABILITY_REGISTRY


def _manifest(**overrides: bool) -> dict[str, bool]:
    manifest = {key: False for key in CAPABILITY_REGISTRY}
    manifest.update(overrides)
    return manifest


def test_state_workflow_merges_optional_execution_state_dumpers() -> None:
    entry = SimpleNamespace(
        target_aggregate=SimpleNamespace(to_snapshot=lambda: {"target": "ok"}),
        position_aggregate=SimpleNamespace(to_snapshot=lambda: {"positions": []}),
        combination_aggregate=SimpleNamespace(to_snapshot=lambda: {"combinations": []}),
        current_dt=datetime(2026, 3, 24, 13, 0, 0),
        runtime=SimpleNamespace(
            state=SimpleNamespace(
                snapshot_dumpers=[
                    lambda target, position, combination, strategy_entry: {
                        "execution_state": {"positions": {"IO2506-C-3800.CFFEX": "working"}}
                    }
                ]
            )
        ),
        logger=SimpleNamespace(error=lambda *args, **kwargs: None),
    )

    snapshot = StateWorkflow(entry).create_snapshot()

    assert snapshot["execution_state"] == {"positions": {"IO2506-C-3800.CFFEX": "working"}}


def test_state_workflow_does_not_dump_execution_state_without_hooks() -> None:
    entry = SimpleNamespace(
        target_aggregate=SimpleNamespace(to_snapshot=lambda: {"target": "ok"}),
        position_aggregate=SimpleNamespace(to_snapshot=lambda: {"positions": []}),
        combination_aggregate=SimpleNamespace(to_snapshot=lambda: {"combinations": []}),
        current_dt=datetime(2026, 3, 24, 13, 0, 0),
        runtime=SimpleNamespace(state=SimpleNamespace(snapshot_dumpers=[])),
        logger=SimpleNamespace(error=lambda *args, **kwargs: None),
    )

    snapshot = StateWorkflow(entry).create_snapshot()

    assert "execution_state" not in snapshot


def test_lifecycle_on_init_runs_optional_restore_hooks_after_oms_sync(monkeypatch) -> None:
    calls: list[str] = []
    runtime = SimpleNamespace(
        lifecycle=SimpleNamespace(init_hooks=[]),
        state=SimpleNamespace(restore_hooks=[lambda entry: calls.append(f"restore:{entry.strategy_name}")]),
    )
    service_cls = type("Service", (), {"__init__": lambda self, **kwargs: None})

    entry = SimpleNamespace(
        logger=SimpleNamespace(
            info=lambda *a, **k: None,
            warning=lambda *a, **k: None,
            error=lambda *a, **k: None,
        ),
        setting={
            "strategy_full_config": {
                "service_activation": _manifest(),
                "strategy_contracts": {},
                "observability": {},
            },
            "bar_window": 0,
        },
        strategy_name="demo",
        max_positions=5,
        strike_level=3,
        backtesting=False,
        warmup_days=1,
        history_repo=SimpleNamespace(replay_bars_from_database=lambda **kwargs: True),
        feishu_webhook="",
        vt_symbols=[],
        trading=True,
        _init_subscription_management=lambda: None,
        _record_snapshot=lambda: None,
        _validate_universe=lambda: None,
        on_bars=lambda bars: None,
    )

    monkeypatch.setattr(
        "src.main.config.config_loader.ConfigLoader.load_target_products",
        lambda: ["IF"],
    )
    monkeypatch.setattr(
        "src.main.config.config_loader.ConfigLoader.import_from_string",
        lambda _: service_cls,
    )
    monkeypatch.setattr(
        "src.main.config.config_loader.ConfigLoader.resolve_service_activation",
        lambda full_config: dict(full_config["service_activation"]),
    )
    monkeypatch.setattr(
        "src.main.config.config_loader.ConfigLoader.load_toml",
        lambda path: {"enabled": False},
    )
    monkeypatch.setattr(
        "src.main.config.domain_service_config_loader.load_position_sizing_config",
        lambda overrides=None: {},
    )
    monkeypatch.setattr(
        "src.main.config.domain_service_config_loader.load_pricing_engine_config",
        lambda overrides=None: {},
    )
    monkeypatch.setattr(
        "src.main.config.domain_service_config_loader.load_future_selector_config",
        lambda overrides=None: {},
    )
    monkeypatch.setattr(
        "src.main.config.domain_service_config_loader.load_option_selector_config",
        lambda overrides=None: {},
    )
    monkeypatch.setattr(
        "src.main.bootstrap.database_factory.DatabaseFactory.get_instance",
        lambda: object(),
    )

    monkeypatch.setattr(
        "src.strategy.application.lifecycle_workflow.InstrumentManager",
        lambda: SimpleNamespace(get_all_active_contracts=lambda: []),
    )
    monkeypatch.setattr(
        "src.strategy.application.lifecycle_workflow.PositionAggregate",
        lambda: SimpleNamespace(),
    )
    monkeypatch.setattr(
        "src.strategy.application.lifecycle_workflow.CombinationAggregate",
        lambda: SimpleNamespace(),
    )
    monkeypatch.setattr(
        "src.strategy.application.lifecycle_workflow.VnpyMarketDataGateway",
        lambda entry: SimpleNamespace(),
    )
    monkeypatch.setattr(
        "src.strategy.application.lifecycle_workflow.VnpyAccountGateway",
        lambda entry: SimpleNamespace(),
    )
    monkeypatch.setattr(
        "src.strategy.application.lifecycle_workflow.VnpyOrderGateway",
        lambda entry: SimpleNamespace(),
    )
    monkeypatch.setattr(
        "src.strategy.application.lifecycle_workflow.VnpyTradeExecutionGateway",
        lambda entry: SimpleNamespace(),
    )
    monkeypatch.setattr(
        "src.strategy.application.lifecycle_workflow.JsonSerializer",
        lambda: SimpleNamespace(),
    )
    monkeypatch.setattr(
        "src.strategy.application.lifecycle_workflow.StateRepository",
        lambda **kwargs: SimpleNamespace(load=lambda strategy_name: ArchiveNotFound(strategy_name=strategy_name)),
    )
    monkeypatch.setattr(
        "src.strategy.application.lifecycle_workflow.AutoSaveService",
        lambda **kwargs: SimpleNamespace(),
    )
    monkeypatch.setattr(
        "src.strategy.application.lifecycle_workflow.build_runtime",
        lambda *args, **kwargs: runtime,
        raising=False,
    )
    monkeypatch.setattr(
        LifecycleWorkflow,
        "_sync_live_oms_snapshot",
        lambda self: calls.append("oms"),
    )

    LifecycleWorkflow(entry).on_init()

    assert calls == ["oms", "restore:demo"]
