from __future__ import annotations

from src.strategy.domain.aggregate.position_aggregate import PositionAggregate
from src.strategy.domain.entity.order import Order, OrderOwnershipScope
from src.strategy.domain.value_object.trading import Direction, Offset


def test_order_ownership_scope_defaults_to_managed_for_short_open() -> None:
    order = Order(
        vt_orderid="ORDER-1",
        vt_symbol="IO2506-C-3800.CFFEX",
        direction=Direction.SHORT,
        offset=Offset.OPEN,
        volume=1,
    )

    assert order.ownership_scope == OrderOwnershipScope.MANAGED_ACTIONABLE
    assert order.is_strategy_actionable is True
    assert order.is_observed_external is False


def test_order_ownership_scope_defaults_to_observed_for_non_managed_shape() -> None:
    order = Order(
        vt_orderid="ORDER-2",
        vt_symbol="IO2506-C-3800.CFFEX",
        direction=Direction.LONG,
        offset=Offset.OPEN,
        volume=1,
    )

    assert order.ownership_scope == OrderOwnershipScope.OBSERVED_EXTERNAL
    assert order.is_strategy_actionable is False
    assert order.is_observed_external is True


def test_exit_intent_requires_higher_priority_to_replace_existing_intent() -> None:
    aggregate = PositionAggregate()

    created = aggregate.ensure_exit_intent(
        subject_key="IO2506-C-3800.CFFEX",
        reason_code="guarded_exit",
        priority=50,
        scope_key="underlying:IF2506.CFFEX",
        override_price=10.5,
        metadata={"source": "guard"},
    )

    rejected = aggregate.ensure_exit_intent(
        subject_key="IO2506-C-3800.CFFEX",
        reason_code="lower_exit",
        priority=40,
        scope_key="underlying:IF2506.CFFEX",
    )

    replaced = aggregate.ensure_exit_intent(
        subject_key="IO2506-C-3800.CFFEX",
        reason_code="higher_exit",
        priority=80,
        scope_key="underlying:IF2506.CFFEX",
    )

    intent = aggregate.get_exit_intent("IO2506-C-3800.CFFEX")

    assert created is True
    assert rejected is False
    assert replaced is True
    assert intent is not None
    assert intent.reason_code == "higher_exit"
    assert intent.priority == 80
    assert intent.scope_key == "underlying:IF2506.CFFEX"


def test_position_aggregate_snapshot_roundtrip_preserves_exit_intents() -> None:
    aggregate = PositionAggregate()
    aggregate.ensure_exit_intent(
        subject_key="IO2506-C-3800.CFFEX",
        reason_code="portfolio_exit",
        priority=70,
        scope_key="portfolio:default",
        metadata={"attempt": 1},
    )

    restored = PositionAggregate.from_snapshot(aggregate.to_snapshot())
    intent = restored.get_exit_intent("IO2506-C-3800.CFFEX")

    assert intent is not None
    assert intent.reason_code == "portfolio_exit"
    assert intent.priority == 70
    assert intent.scope_key == "portfolio:default"
    assert intent.metadata == {"attempt": 1}


def test_scope_exit_preempt_summary_reports_locked_when_any_reason_is_pending() -> None:
    aggregate = PositionAggregate()

    aggregate.upsert_exit_preempt_state(
        scope_key="underlying:IF2506.CFFEX",
        reason_code="guarded_exit",
        pending=True,
        pending_reason="waiting_freshness",
    )

    summary = aggregate.get_scope_exit_preempt_summary("underlying:IF2506.CFFEX")
    state = aggregate.get_exit_preempt_state("underlying:IF2506.CFFEX", "guarded_exit")

    assert summary["locked"] is True
    assert summary["active_reason_codes"] == ["guarded_exit"]
    assert state.pending is True
    assert state.pending_reason == "waiting_freshness"
    assert state.locked is True


def test_scope_exit_preempt_summary_roundtrip_preserves_reason_state() -> None:
    aggregate = PositionAggregate()
    aggregate.upsert_exit_preempt_state(
        scope_key="portfolio:default",
        reason_code="priority_exit",
        condition_active=True,
        inflight=True,
    )

    restored = PositionAggregate.from_snapshot(aggregate.to_snapshot())
    summary = restored.get_scope_exit_preempt_summary("portfolio:default")
    state = restored.get_exit_preempt_state("portfolio:default", "priority_exit")

    assert summary["locked"] is True
    assert summary["active_reason_codes"] == ["priority_exit"]
    assert state.condition_active is True
    assert state.inflight is True
    assert state.locked is True


def test_pending_order_views_follow_ownership_scope() -> None:
    aggregate = PositionAggregate()
    managed_order = Order(
        vt_orderid="ORDER-1",
        vt_symbol="IO2506-C-3800.CFFEX",
        direction=Direction.SHORT,
        offset=Offset.OPEN,
        volume=1,
    )
    observed_order = Order(
        vt_orderid="ORDER-2",
        vt_symbol="IO2506-C-3900.CFFEX",
        direction=Direction.LONG,
        offset=Offset.OPEN,
        volume=1,
    )
    aggregate.add_pending_order(managed_order)
    aggregate.add_pending_order(observed_order)

    actionable_ids = [order.vt_orderid for order in aggregate.get_strategy_actionable_orders()]
    observed_ids = [order.vt_orderid for order in aggregate.get_observed_external_orders()]

    assert actionable_ids == ["ORDER-1"]
    assert observed_ids == ["ORDER-2"]
