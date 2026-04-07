from __future__ import annotations

from types import SimpleNamespace

from src.strategy.application.exit_workflow import ExitWorkflow
from src.strategy.domain.aggregate.position_aggregate import PositionAggregate
from src.strategy.domain.domain_service.execution.exit_recovery_service import ExitRecoveryAction
from src.strategy.domain.value_object.trading.freshness_check import (
    FreshnessCheckResult,
    FreshnessState,
)


def _entry() -> SimpleNamespace:
    return SimpleNamespace(position_aggregate=PositionAggregate())


def test_exit_workflow_records_generic_exit_intent() -> None:
    entry = _entry()

    created = ExitWorkflow(entry).ensure_exit_intent(
        subject_key="IO2506-C-3800.CFFEX",
        reason_code="guarded_exit",
        priority=60,
        scope_key="underlying:IF2506.CFFEX",
    )

    intent = entry.position_aggregate.get_exit_intent("IO2506-C-3800.CFFEX")

    assert created is True
    assert intent is not None
    assert intent.reason_code == "guarded_exit"


def test_exit_workflow_defers_recovery_by_marking_pending_scope_state() -> None:
    entry = _entry()
    workflow = ExitWorkflow(entry)
    workflow.ensure_exit_intent(
        subject_key="IO2506-C-3800.CFFEX",
        reason_code="guarded_exit",
        priority=60,
        scope_key="underlying:IF2506.CFFEX",
    )

    decision = workflow.apply_recovery_decision(
        subject_key="IO2506-C-3800.CFFEX",
        scope_key="underlying:IF2506.CFFEX",
        reason_code="guarded_exit",
        freshness=FreshnessCheckResult(
            state=FreshnessState.STALE,
            detail="mirror not ready",
        ),
        remaining_exposure=2,
    )

    state = entry.position_aggregate.get_exit_preempt_state(
        "underlying:IF2506.CFFEX",
        "guarded_exit",
    )

    assert decision.action == ExitRecoveryAction.DEFER
    assert state.pending is True
    assert state.pending_reason == "stale"


def test_exit_workflow_clears_intent_when_recovery_says_exposure_is_gone() -> None:
    entry = _entry()
    workflow = ExitWorkflow(entry)
    workflow.ensure_exit_intent(
        subject_key="IO2506-C-3800.CFFEX",
        reason_code="guarded_exit",
        priority=60,
        scope_key="underlying:IF2506.CFFEX",
    )
    entry.position_aggregate.upsert_exit_preempt_state(
        scope_key="underlying:IF2506.CFFEX",
        reason_code="guarded_exit",
        pending=True,
        pending_reason="retry_ready",
    )

    decision = workflow.apply_recovery_decision(
        subject_key="IO2506-C-3800.CFFEX",
        scope_key="underlying:IF2506.CFFEX",
        reason_code="guarded_exit",
        freshness=FreshnessCheckResult.ready(detail="fresh"),
        remaining_exposure=0,
    )

    summary = entry.position_aggregate.get_scope_exit_preempt_summary("underlying:IF2506.CFFEX")

    assert decision.action == ExitRecoveryAction.CLEAR
    assert entry.position_aggregate.get_exit_intent("IO2506-C-3800.CFFEX") is None
    assert summary["locked"] is False
