"""Generic exit orchestration workflow primitives."""

from __future__ import annotations

from typing import Any, Dict, Optional, TYPE_CHECKING

from ..domain.domain_service.execution.exit_recovery_service import ExitRecoveryDecision, ExitRecoveryService
from ..domain.value_object.trading.freshness_check import FreshnessCheckResult

if TYPE_CHECKING:
    from src.strategy.strategy_entry import StrategyEntry


class ExitWorkflow:
    """Thin application bridge for generic exit intent and recovery state."""

    def __init__(self, entry: "StrategyEntry") -> None:
        self.entry = entry

    def ensure_exit_intent(
        self,
        *,
        subject_key: str,
        reason_code: str,
        priority: int,
        scope_key: str = "",
        override_price: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        return self.entry.position_aggregate.ensure_exit_intent(
            subject_key=subject_key,
            reason_code=reason_code,
            priority=priority,
            scope_key=scope_key,
            override_price=override_price,
            metadata=metadata,
        )

    def apply_recovery_decision(
        self,
        *,
        subject_key: str,
        scope_key: str,
        reason_code: str,
        freshness: FreshnessCheckResult,
        remaining_exposure: int,
    ) -> ExitRecoveryDecision:
        decision = ExitRecoveryService.decide(
            freshness=freshness,
            remaining_exposure=remaining_exposure,
        )
        aggregate = self.entry.position_aggregate

        if decision.action.value == "defer":
            aggregate.upsert_exit_preempt_state(
                scope_key=scope_key,
                reason_code=reason_code,
                pending=True,
                pending_reason=freshness.state.value,
            )
        elif decision.action.value == "clear":
            aggregate.clear_exit_preempt_state(scope_key, reason_code)
            aggregate.drop_exit_intent(subject_key)
        else:
            aggregate.upsert_exit_preempt_state(
                scope_key=scope_key,
                reason_code=reason_code,
                pending=True,
                pending_reason="retry_ready",
            )
        return decision
