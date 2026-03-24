from __future__ import annotations

from datetime import datetime

import pytest

from src.strategy.domain.aggregate.position_aggregate import PositionAggregate
from src.strategy.domain.event.event_types import (
    ExecutionPreemptedEvent,
    LegExecutionBlockedEvent,
)
from src.strategy.domain.value_object.trading import Direction, Offset, OrderInstruction
from src.strategy.domain.value_object.trading.execution_state import (
    ExecutionAction,
    ExecutionPhase,
    ExecutionPriority,
)


def _seed_position(target_volume: int = 3, filled_volume: int = 3) -> tuple[PositionAggregate, str]:
    aggregate = PositionAggregate()
    position = aggregate.create_position(
        option_vt_symbol="IO2506-C-3800.CFFEX",
        underlying_vt_symbol="IF2506.CFFEX",
        signal="seed",
        target_volume=target_volume,
    )
    position.volume = filled_volume
    return aggregate, position.vt_symbol


def _close_instruction(vt_symbol: str, volume: int) -> OrderInstruction:
    return OrderInstruction(
        vt_symbol=vt_symbol,
        direction=Direction.LONG,
        offset=Offset.CLOSE,
        volume=volume,
        price=10.0,
        signal="close",
    )


def _open_instruction(vt_symbol: str, volume: int) -> OrderInstruction:
    return OrderInstruction(
        vt_symbol=vt_symbol,
        direction=Direction.SHORT,
        offset=Offset.OPEN,
        volume=volume,
        price=10.0,
        signal="open",
    )


def test_begin_execution_intent_blocks_repeat_submission_during_cancel_pending() -> None:
    aggregate, vt_symbol = _seed_position()

    aggregate.begin_execution_intent(
        vt_symbol=vt_symbol,
        intent_id="tp-close",
        action=ExecutionAction.CLOSE,
        priority=ExecutionPriority.TAKE_PROFIT,
        requested_volume=3,
        reason="take profit",
    )
    aggregate.pop_domain_events()

    aggregate.bind_order(vt_symbol, "ORDER-1", _close_instruction(vt_symbol, 3))
    aggregate.request_cancel(vt_symbol, reason="timeout")

    assert aggregate.get_execution_state(vt_symbol).phase == ExecutionPhase.CANCEL_PENDING

    with pytest.raises(RuntimeError):
        aggregate.begin_execution_intent(
            vt_symbol=vt_symbol,
            intent_id="tp-close-2",
            action=ExecutionAction.CLOSE,
            priority=ExecutionPriority.TAKE_PROFIT,
            requested_volume=3,
            reason="repeat close",
        )

    events = aggregate.pop_domain_events()
    assert any(isinstance(event, LegExecutionBlockedEvent) for event in events)


def test_higher_priority_intent_preempts_existing_leg_execution() -> None:
    aggregate, vt_symbol = _seed_position()

    aggregate.begin_execution_intent(
        vt_symbol=vt_symbol,
        intent_id="tp-close",
        action=ExecutionAction.CLOSE,
        priority=ExecutionPriority.TAKE_PROFIT,
        requested_volume=3,
        reason="take profit",
    )
    aggregate.bind_order(vt_symbol, "ORDER-1", _close_instruction(vt_symbol, 3))
    aggregate.pop_domain_events()

    state = aggregate.begin_execution_intent(
        vt_symbol=vt_symbol,
        intent_id="risk-close",
        action=ExecutionAction.CLOSE,
        priority=ExecutionPriority.RISK,
        requested_volume=3,
        reason="risk stop",
    )

    assert state.intent_id == "risk-close"
    assert state.phase == ExecutionPhase.RESERVED
    assert state.priority == ExecutionPriority.RISK

    events = aggregate.pop_domain_events()
    assert any(isinstance(event, ExecutionPreemptedEvent) for event in events)


def test_partial_fill_moves_leg_execution_to_partial_filled() -> None:
    aggregate, vt_symbol = _seed_position(target_volume=2, filled_volume=0)

    aggregate.begin_execution_intent(
        vt_symbol=vt_symbol,
        intent_id="open-1",
        action=ExecutionAction.OPEN,
        priority=ExecutionPriority.OPEN_SIGNAL,
        requested_volume=2,
        reason="open signal",
    )
    aggregate.pop_domain_events()

    aggregate.bind_order(vt_symbol, "ORDER-OPEN-1", _open_instruction(vt_symbol, 2))
    aggregate.update_from_order(
        {
            "vt_orderid": "ORDER-OPEN-1",
            "vt_symbol": vt_symbol,
            "status": "parttraded",
            "traded": 1,
        }
    )
    aggregate.update_from_trade(
        {
            "vt_symbol": vt_symbol,
            "volume": 1,
            "offset": "open",
            "price": 10.0,
            "datetime": datetime(2026, 3, 24, 13, 0, 0),
        }
    )

    state = aggregate.get_execution_state(vt_symbol)
    assert state.phase == ExecutionPhase.PARTIAL_FILLED
    assert state.filled_volume == 1


def test_reserved_open_volume_comes_from_execution_state() -> None:
    aggregate, vt_symbol = _seed_position(target_volume=5, filled_volume=0)

    aggregate.begin_execution_intent(
        vt_symbol=vt_symbol,
        intent_id="open-1",
        action=ExecutionAction.OPEN,
        priority=ExecutionPriority.OPEN_SIGNAL,
        requested_volume=5,
        reason="open signal",
    )
    aggregate.update_from_trade(
        {
            "vt_symbol": vt_symbol,
            "volume": 2,
            "offset": "open",
            "price": 10.0,
            "datetime": datetime(2026, 3, 24, 13, 5, 0),
        }
    )

    assert aggregate.get_reserved_open_volume(vt_symbol) == 3
