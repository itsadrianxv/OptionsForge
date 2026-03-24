from __future__ import annotations

from datetime import datetime

import pytest

from src.strategy.domain.aggregate.combination_aggregate import CombinationAggregate
from src.strategy.domain.entity.combination import Combination
from src.strategy.domain.event.event_types import (
    CombinationExecutionFailedEvent,
    ExecutionPreemptedEvent,
    LegExecutionBlockedEvent,
)
from src.strategy.domain.value_object.combination import CombinationStatus, CombinationType, Leg
from src.strategy.domain.value_object.trading.execution_state import (
    ExecutionAction,
    ExecutionMode,
    ExecutionPhase,
    ExecutionPriority,
)


def _build_combination() -> Combination:
    return Combination(
        combination_id="combo-1",
        combination_type=CombinationType.STRANGLE,
        underlying_vt_symbol="IF2506.CFFEX",
        legs=[
            Leg(
                vt_symbol="IO2506-C-3800.CFFEX",
                option_type="call",
                strike_price=3800,
                expiry_date="2026-06-20",
                direction="short",
                volume=1,
                open_price=10.0,
            ),
            Leg(
                vt_symbol="IO2506-P-3600.CFFEX",
                option_type="put",
                strike_price=3600,
                expiry_date="2026-06-20",
                direction="short",
                volume=1,
                open_price=11.0,
            ),
        ],
        status=CombinationStatus.ACTIVE,
        create_time=datetime(2026, 3, 24, 13, 0, 0),
    )


def test_combination_enters_degraded_then_failed_when_all_legs_required_breaks() -> None:
    aggregate = CombinationAggregate()
    combination = _build_combination()
    aggregate.register_combination(combination)

    aggregate.acquire_combination_intent(
        combination_id=combination.combination_id,
        intent_id="combo-open-1",
        action=ExecutionAction.OPEN_COMBO,
        priority=ExecutionPriority.OPEN_SIGNAL,
        execution_mode=ExecutionMode.ALL_LEGS_REQUIRED,
        reason="open combo",
    )
    aggregate.attach_leg_intent(combination.combination_id, combination.legs[0].vt_symbol, "leg-1")
    aggregate.attach_leg_intent(combination.combination_id, combination.legs[1].vt_symbol, "leg-2")
    aggregate.pop_domain_events()

    aggregate.update_leg_phase(
        combination.combination_id,
        combination.legs[0].vt_symbol,
        ExecutionPhase.WORKING,
    )
    aggregate.update_leg_phase(
        combination.combination_id,
        combination.legs[1].vt_symbol,
        ExecutionPhase.FAILED,
    )

    assert aggregate.get_execution_state(combination.combination_id).phase == ExecutionPhase.DEGRADED

    aggregate.update_leg_phase(
        combination.combination_id,
        combination.legs[0].vt_symbol,
        ExecutionPhase.COMPLETED,
    )

    state = aggregate.get_execution_state(combination.combination_id)
    assert state.phase == ExecutionPhase.FAILED

    events = aggregate.pop_domain_events()
    assert any(isinstance(event, CombinationExecutionFailedEvent) for event in events)


def test_combination_enters_partial_when_leg_fill_states_diverge() -> None:
    aggregate = CombinationAggregate()
    combination = _build_combination()
    aggregate.register_combination(combination)

    aggregate.acquire_combination_intent(
        combination_id=combination.combination_id,
        intent_id="combo-open-1",
        action=ExecutionAction.OPEN_COMBO,
        priority=ExecutionPriority.OPEN_SIGNAL,
        execution_mode=ExecutionMode.ALL_LEGS_REQUIRED,
        reason="open combo",
    )
    aggregate.attach_leg_intent(combination.combination_id, combination.legs[0].vt_symbol, "leg-1")
    aggregate.attach_leg_intent(combination.combination_id, combination.legs[1].vt_symbol, "leg-2")

    aggregate.update_leg_phase(
        combination.combination_id,
        combination.legs[0].vt_symbol,
        ExecutionPhase.PARTIAL_FILLED,
    )
    aggregate.update_leg_phase(
        combination.combination_id,
        combination.legs[1].vt_symbol,
        ExecutionPhase.WORKING,
    )

    state = aggregate.get_execution_state(combination.combination_id)
    assert state.phase == ExecutionPhase.PARTIAL


def test_combination_priority_preemption_is_explicit() -> None:
    aggregate = CombinationAggregate()
    combination = _build_combination()
    aggregate.register_combination(combination)

    aggregate.acquire_combination_intent(
        combination_id=combination.combination_id,
        intent_id="rebalance-1",
        action=ExecutionAction.REBALANCE,
        priority=ExecutionPriority.REBALANCE,
        execution_mode=ExecutionMode.BEST_EFFORT,
        reason="rebalance",
    )
    aggregate.pop_domain_events()

    with pytest.raises(RuntimeError):
        aggregate.acquire_combination_intent(
            combination_id=combination.combination_id,
            intent_id="open-1",
            action=ExecutionAction.OPEN_COMBO,
            priority=ExecutionPriority.OPEN_SIGNAL,
            execution_mode=ExecutionMode.ALL_LEGS_REQUIRED,
            reason="open combo",
        )

    blocked_events = aggregate.pop_domain_events()
    assert any(isinstance(event, LegExecutionBlockedEvent) for event in blocked_events)

    state = aggregate.acquire_combination_intent(
        combination_id=combination.combination_id,
        intent_id="risk-1",
        action=ExecutionAction.CLOSE_COMBO,
        priority=ExecutionPriority.RISK,
        execution_mode=ExecutionMode.ALL_LEGS_REQUIRED,
        reason="risk close",
    )

    assert state.intent_id == "risk-1"
    assert state.priority == ExecutionPriority.RISK

    events = aggregate.pop_domain_events()
    assert any(isinstance(event, ExecutionPreemptedEvent) for event in events)
