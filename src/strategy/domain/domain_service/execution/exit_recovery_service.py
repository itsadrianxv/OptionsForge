from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from ...value_object.trading.freshness_check import FreshnessCheckResult


class ExitRecoveryAction(Enum):
    DEFER = "defer"
    CLEAR = "clear"
    RETRY = "retry"


@dataclass(frozen=True)
class ExitRecoveryDecision:
    action: ExitRecoveryAction
    keep_pending: bool
    clear_intent: bool
    detail: str = ""


class ExitRecoveryService:
    """基于 freshness 与剩余义务生成通用恢复动作。"""

    @staticmethod
    def decide(
        *,
        freshness: FreshnessCheckResult,
        remaining_exposure: int,
    ) -> ExitRecoveryDecision:
        if not freshness.is_ready:
            return ExitRecoveryDecision(
                action=ExitRecoveryAction.DEFER,
                keep_pending=True,
                clear_intent=False,
                detail=freshness.detail,
            )

        if int(remaining_exposure) <= 0:
            return ExitRecoveryDecision(
                action=ExitRecoveryAction.CLEAR,
                keep_pending=False,
                clear_intent=True,
                detail="remaining exposure cleared",
            )

        return ExitRecoveryDecision(
            action=ExitRecoveryAction.RETRY,
            keep_pending=True,
            clear_intent=False,
            detail="freshness ready and exposure remains",
        )
