from __future__ import annotations

from src.strategy.domain.domain_service.execution.exit_recovery_service import (
    ExitRecoveryAction,
    ExitRecoveryService,
)
from src.strategy.domain.value_object.trading.freshness_check import (
    FreshnessCheckResult,
    FreshnessState,
)


def test_exit_recovery_defers_when_freshness_is_not_ready() -> None:
    decision = ExitRecoveryService.decide(
        freshness=FreshnessCheckResult(
            state=FreshnessState.MISMATCH,
            detail="broker and mirror disagree",
        ),
        remaining_exposure=3,
    )

    assert decision.action == ExitRecoveryAction.DEFER
    assert decision.keep_pending is True
    assert decision.clear_intent is False


def test_exit_recovery_clears_when_remaining_exposure_is_gone() -> None:
    decision = ExitRecoveryService.decide(
        freshness=FreshnessCheckResult.ready(detail="fresh"),
        remaining_exposure=0,
    )

    assert decision.action == ExitRecoveryAction.CLEAR
    assert decision.keep_pending is False
    assert decision.clear_intent is True


def test_exit_recovery_retries_when_freshness_is_ready_and_exposure_remains() -> None:
    decision = ExitRecoveryService.decide(
        freshness=FreshnessCheckResult.ready(detail="fresh"),
        remaining_exposure=2,
    )

    assert decision.action == ExitRecoveryAction.RETRY
    assert decision.keep_pending is True
    assert decision.clear_intent is False
