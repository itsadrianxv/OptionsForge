from contextlib import contextmanager
from unittest.mock import patch

from src.strategy.infrastructure.monitoring.notification_protocol import (
    MONITOR_DECISION_TRACE_UPDATES_CHANNEL,
    MONITOR_SNAPSHOT_UPDATES_CHANNEL,
)
from src.strategy.infrastructure.monitoring.strategy_monitor import StrategyMonitor


class _FakeCursor:
    def __init__(self, row=None):
        self._row = row

    def fetchone(self):
        return self._row


class _FakeDatabase:
    def __init__(self, rows=None):
        self.rows = list(rows or [])
        self.calls = []

    @contextmanager
    def connection_context(self):
        yield self

    def execute_sql(self, sql, params=None):
        self.calls.append((sql, params))
        row = self.rows.pop(0) if self.rows else None
        return _FakeCursor(row)


def _build_monitor() -> StrategyMonitor:
    return StrategyMonitor(
        variant_name="alpha",
        monitor_instance_id="default",
        monitor_db_config={"host": "localhost", "user": "tester", "database": "monitor"},
    )


def test_insert_monitor_event_notifies_only_for_new_decision_trace() -> None:
    monitor = _build_monitor()
    fake_db = _FakeDatabase(rows=[(123,), None])

    with patch.object(monitor, "_ensure_monitor_tables"), patch.object(
        monitor, "_monitor_db_connect", return_value=fake_db
    ), patch.object(monitor, "_bind_models"):
        inserted_id = monitor.insert_monitor_event(
            event_type="decision_trace",
            event_key="trace-123",
            payload={"trace_id": "trace-123", "stages": []},
            vt_symbol="rb2501.SHFE",
            bar_dt=None,
        )

    assert inserted_id == 123
    assert any("INSERT INTO monitor_signal_event" in sql for sql, _ in fake_db.calls)
    assert any(
        params and params[0] == MONITOR_DECISION_TRACE_UPDATES_CHANNEL
        for _, params in fake_db.calls
        if params
    )


def test_insert_monitor_event_duplicate_skips_notify() -> None:
    monitor = _build_monitor()
    fake_db = _FakeDatabase(rows=[None])

    with patch.object(monitor, "_ensure_monitor_tables"), patch.object(
        monitor, "_monitor_db_connect", return_value=fake_db
    ), patch.object(monitor, "_bind_models"):
        inserted_id = monitor.insert_monitor_event(
            event_type="decision_trace",
            event_key="trace-123",
            payload={"trace_id": "trace-123", "stages": []},
            vt_symbol="rb2501.SHFE",
            bar_dt=None,
        )

    assert inserted_id is None
    assert any("INSERT INTO monitor_signal_event" in sql for sql, _ in fake_db.calls)
    assert not any(
        params and params[0] == MONITOR_DECISION_TRACE_UPDATES_CHANNEL
        for _, params in fake_db.calls
        if params
    )


def test_upsert_monitor_snapshot_sends_notify() -> None:
    monitor = _build_monitor()
    fake_db = _FakeDatabase(rows=[None, None])

    with patch.object(monitor, "_ensure_monitor_tables"), patch.object(
        monitor, "_monitor_db_connect", return_value=fake_db
    ), patch.object(monitor, "_bind_models"):
        monitor._upsert_monitor_snapshot(
            payload={
                "timestamp": "2026-03-17 10:00:00",
                "variant": "alpha",
                "instruments": {},
                "positions": [],
                "orders": [],
                "recent_decisions": [],
            },
            bar_dt=None,
            bar_interval=None,
            bar_window=None,
        )

    assert any("INSERT INTO monitor_signal_snapshot" in sql for sql, _ in fake_db.calls)
    assert any(
        params and params[0] == MONITOR_SNAPSHOT_UPDATES_CHANNEL
        for _, params in fake_db.calls
        if params
    )
