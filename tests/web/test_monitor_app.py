from __future__ import annotations

from typing import Any, Dict, List, Optional

from src.strategy.infrastructure.monitoring.notification_protocol import (
    MONITOR_DECISION_TRACE_UPDATES_CHANNEL,
    MONITOR_SNAPSHOT_UPDATES_CHANNEL,
)
from src.web.app import create_app, socketio


class _FakeSnapshotReader:
    def __init__(self) -> None:
        self.snapshots = {
            "alpha": {
                "timestamp": "2026-03-17 10:00:00",
                "variant": "alpha",
                "instruments": {},
                "positions": [],
                "orders": [],
                "recent_decisions": [],
            },
            "beta": {
                "timestamp": "2026-03-17 10:01:00",
                "variant": "beta",
                "instruments": {},
                "positions": [],
                "orders": [],
                "recent_decisions": [],
            },
        }
        self.events = {
            1: {
                "id": 1,
                "variant": "alpha",
                "instance_id": "default",
                "vt_symbol": "rb2501.SHFE",
                "bar_dt": "2026-03-17T10:00:00",
                "event_type": "decision_trace",
                "event_key": "alpha-trace",
                "created_at": "2026-03-17T10:00:01",
                "payload": {
                    "trace_id": "alpha-trace",
                    "vt_symbol": "rb2501.SHFE",
                    "signal_name": "open",
                    "stages": [],
                },
            },
            2: {
                "id": 2,
                "variant": "beta",
                "instance_id": "default",
                "vt_symbol": "i2505.DCE",
                "bar_dt": "2026-03-17T10:01:00",
                "event_type": "decision_trace",
                "event_key": "beta-trace",
                "created_at": "2026-03-17T10:01:01",
                "payload": {
                    "trace_id": "beta-trace",
                    "vt_symbol": "i2505.DCE",
                    "signal_name": "close",
                    "stages": [],
                },
            },
        }

    def _db_available(self) -> bool:
        return True

    def ensure_tables(self) -> None:
        return None

    def _connect_listener(self):
        return None

    def list_available_strategies(self) -> List[Dict[str, Any]]:
        return [
            {"variant": "alpha", "last_update": "2026-03-17 10:00:00", "file_size": None},
            {"variant": "beta", "last_update": "2026-03-17 10:01:00", "file_size": None},
        ]

    def get_strategy_data(self, variant: str) -> Optional[Dict[str, Any]]:
        return self.snapshots.get(variant)

    def get_events(
        self,
        variant: str,
        vt_symbol: str = "",
        start: str = "",
        end: str = "",
        event_type: str = "",
        limit: int = 2000,
    ) -> List[Dict[str, Any]]:
        items = [event for event in self.events.values() if event["variant"] == variant]
        if vt_symbol:
            items = [event for event in items if event["vt_symbol"] == vt_symbol]
        if event_type:
            items = [event for event in items if event["event_type"] == event_type]
        return items[:limit]

    def get_event_by_id(self, event_id: int) -> Optional[Dict[str, Any]]:
        return self.events.get(int(event_id))

    def get_bars(
        self,
        vt_symbol: str,
        start: str,
        end: str,
        interval: str = "1m",
        limit: int = 5000,
    ) -> List[Dict[str, Any]]:
        return []


class _FakeStateReader:
    def list_available_strategies(self) -> List[Dict[str, Any]]:
        return [{"variant": "fallback", "last_update": "2026-03-17 09:59:00", "file_size": None}]

    def get_strategy_data(self, variant: str) -> Optional[Dict[str, Any]]:
        if variant != "fallback":
            return None
        return {
            "timestamp": "2026-03-17 09:59:00",
            "variant": "fallback",
            "instruments": {},
            "positions": [],
            "orders": [],
            "recent_decisions": [],
        }


def _received_names(client) -> List[str]:
    return [item["name"] for item in client.get_received()]


def test_api_data_prefers_monitor_snapshot_and_falls_back_to_state() -> None:
    app = create_app(
        start_background_services=False,
        snapshot_reader=_FakeSnapshotReader(),
        state_reader=_FakeStateReader(),
    )
    client = app.test_client()

    snapshot_resp = client.get("/api/data/alpha")
    fallback_resp = client.get("/api/data/fallback")
    strategies_resp = client.get("/api/strategies")

    assert snapshot_resp.status_code == 200
    assert snapshot_resp.get_json()["variant"] == "alpha"
    assert fallback_resp.status_code == 200
    assert fallback_resp.get_json()["variant"] == "fallback"
    assert strategies_resp.get_json() == ["alpha", "beta", "fallback"]


def test_socket_subscription_switches_rooms_for_snapshot_and_event_updates() -> None:
    app = create_app(
        start_background_services=False,
        snapshot_reader=_FakeSnapshotReader(),
        state_reader=_FakeStateReader(),
    )
    runtime = app.extensions["monitor_runtime"]
    client = socketio.test_client(app)

    client.emit("subscribe", {"variant": "alpha"})
    assert "subscription_state" in _received_names(client)

    runtime.process_notification(MONITOR_SNAPSHOT_UPDATES_CHANNEL, {"variant": "alpha"})
    received = client.get_received()
    assert any(item["name"] == "snapshot_update" for item in received)

    client.emit("subscribe", {"variant": "beta"})
    assert "subscription_state" in _received_names(client)

    runtime.process_notification(MONITOR_SNAPSHOT_UPDATES_CHANNEL, {"variant": "alpha"})
    assert not client.get_received()

    runtime.process_notification(MONITOR_SNAPSHOT_UPDATES_CHANNEL, {"variant": "beta"})
    assert any(item["name"] == "snapshot_update" for item in client.get_received())

    runtime.process_notification(
        MONITOR_DECISION_TRACE_UPDATES_CHANNEL,
        {"variant": "beta", "event_id": 2, "event_type": "decision_trace"},
    )
    assert any(item["name"] == "event_new" for item in client.get_received())

    client.disconnect()
