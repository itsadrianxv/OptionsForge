from __future__ import annotations

from types import SimpleNamespace

import src.main.config.gateway_manager as gateway_manager_module
from src.main.config.gateway_manager import GatewayManager


class FakeMainEngine:
    def __init__(self, events: list[str]) -> None:
        self.event_engine = SimpleNamespace()
        self._events = events

    def add_gateway(self, gateway_class) -> None:
        self._events.append("add_gateway")


def test_gateway_manager_patches_ctp_before_adding_gateway(monkeypatch) -> None:
    events: list[str] = []

    def record_patch(_logger) -> None:
        events.append("patch")

    monkeypatch.setattr(
        gateway_manager_module,
        "patch_ctp_pre_settlement_price",
        record_patch,
    )

    main_engine = FakeMainEngine(events)

    manager = GatewayManager(main_engine)
    manager.set_config({"ctp": {}})
    manager.add_gateways()

    assert events[:2] == ["patch", "add_gateway"]
