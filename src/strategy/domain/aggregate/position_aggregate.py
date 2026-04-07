"""Position aggregate with order tracking and leg-level execution state."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Dict, List, Optional, Set

from ..entity.order import Order, OrderStatus
from ..entity.position import Position
from ..event.event_types import (
    DomainEvent,
    ExecutionIntentStartedEvent,
    ExecutionPhaseChangedEvent,
    ExecutionPreemptedEvent,
    LegExecutionBlockedEvent,
    ManualCloseDetectedEvent,
    ManualOpenDetectedEvent,
    PositionClosedEvent,
    RiskLimitExceededEvent,
)
from ..value_object.trading.execution_state import (
    ExecutionAction,
    ExecutionPhase,
    ExecutionPriority,
    PositionExecutionState,
)
from ..value_object.trading.exit_intent import ExitIntent
from ..value_object.trading.exit_preempt_state import ExitPreemptState


class PositionAggregate:
    """Owns strategy positions, pending orders, and leg execution state."""

    def __init__(self) -> None:
        self._positions: Dict[str, Position] = {}
        self._pending_orders: Dict[str, Order] = {}
        self._execution_states: Dict[str, PositionExecutionState] = {}
        self._exit_intents: Dict[str, ExitIntent] = {}
        self._exit_preempt_states: Dict[str, Dict[str, ExitPreemptState]] = {}
        self._managed_symbols: Set[str] = set()
        self._domain_events: List[DomainEvent] = []
        self._daily_open_count_map: Dict[str, int] = {}
        self._global_daily_open_count: int = 0
        self._last_trading_date: Optional[date] = None

    def to_snapshot(self) -> Dict[str, Any]:
        return {
            "positions": self._positions,
            "pending_orders": self._pending_orders,
            "exit_intents": {
                subject_key: intent.to_dict()
                for subject_key, intent in self._exit_intents.items()
            },
            "exit_preempt_states": {
                scope_key: {
                    reason_code: state.to_dict()
                    for reason_code, state in reason_states.items()
                }
                for scope_key, reason_states in self._exit_preempt_states.items()
            },
            "managed_symbols": self._managed_symbols,
            "daily_open_count_map": self._daily_open_count_map,
            "global_daily_open_count": self._global_daily_open_count,
            "last_trading_date": self._last_trading_date,
        }

    @classmethod
    def from_snapshot(cls, snapshot: Dict[str, Any]) -> "PositionAggregate":
        obj = cls()
        obj._positions = snapshot.get("positions", {})
        obj._pending_orders = snapshot.get("pending_orders", {})
        obj._exit_intents = {
            str(subject_key): (
                intent
                if isinstance(intent, ExitIntent)
                else ExitIntent.from_dict(dict(intent or {}))
            )
            for subject_key, intent in dict(snapshot.get("exit_intents", {}) or {}).items()
        }
        obj._exit_preempt_states = {
            str(scope_key): {
                str(reason_code): (
                    state
                    if isinstance(state, ExitPreemptState)
                    else ExitPreemptState.from_dict(dict(state or {}))
                )
                for reason_code, state in dict(reason_states or {}).items()
            }
            for scope_key, reason_states in dict(snapshot.get("exit_preempt_states", {}) or {}).items()
        }
        obj._managed_symbols = snapshot.get("managed_symbols", set())
        obj._daily_open_count_map = snapshot.get("daily_open_count_map", {})
        obj._global_daily_open_count = snapshot.get("global_daily_open_count", 0)
        obj._last_trading_date = snapshot.get("last_trading_date", None)
        for vt_symbol in obj._managed_symbols:
            obj._execution_states[vt_symbol] = PositionExecutionState(vt_symbol=vt_symbol)
        return obj

    def create_position(
        self,
        option_vt_symbol: str,
        underlying_vt_symbol: str,
        signal: str,
        target_volume: int,
    ) -> Position:
        position = Position(
            vt_symbol=option_vt_symbol,
            underlying_vt_symbol=underlying_vt_symbol,
            signal=signal,
            target_volume=target_volume,
        )
        self._positions[option_vt_symbol] = position
        self._managed_symbols.add(option_vt_symbol)
        self._ensure_execution_state(option_vt_symbol)
        return position

    def get_position(self, vt_symbol: str) -> Optional[Position]:
        return self._positions.get(vt_symbol)

    def get_positions_by_underlying(self, underlying_vt_symbol: str) -> List[Position]:
        return [
            position
            for position in self._positions.values()
            if position.underlying_vt_symbol == underlying_vt_symbol
            and not position.is_closed
            and position.volume > 0
        ]

    def get_active_positions(self) -> List[Position]:
        return [position for position in self._positions.values() if position.is_active]

    def get_all_positions(self) -> List[Position]:
        return list(self._positions.values())

    def get_closed_vt_symbols(self) -> Set[str]:
        return {position.vt_symbol for position in self._positions.values() if position.is_closed}

    def add_pending_order(self, order: Order) -> None:
        self._pending_orders[order.vt_orderid] = order

    def bind_order(self, vt_symbol: str, vt_orderid: str, instruction: Any) -> Order:
        state = self._ensure_execution_state(vt_symbol)
        order = Order(
            vt_orderid=vt_orderid,
            vt_symbol=vt_symbol,
            direction=instruction.direction,
            offset=instruction.offset,
            volume=instruction.volume,
            price=instruction.price,
            signal=getattr(instruction, "signal", ""),
        )
        self._pending_orders[vt_orderid] = order
        state.active_order_ids.add(vt_orderid)
        self._set_phase(state, ExecutionPhase.SUBMITTING, "bind_order")
        return order

    def get_pending_order(self, vt_orderid: str) -> Optional[Order]:
        return self._pending_orders.get(vt_orderid)

    def get_all_pending_orders(self) -> List[Order]:
        return list(self._pending_orders.values())

    def get_strategy_actionable_orders(self) -> List[Order]:
        return [
            order
            for order in self._pending_orders.values()
            if order.is_strategy_actionable
        ]

    def get_observed_external_orders(self) -> List[Order]:
        return [
            order
            for order in self._pending_orders.values()
            if order.is_observed_external
        ]

    def get_execution_state(self, vt_symbol: str) -> PositionExecutionState:
        return self._ensure_execution_state(vt_symbol)

    def get_all_execution_states(self) -> Dict[str, PositionExecutionState]:
        return dict(self._execution_states)

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
        subject = str(subject_key or "")
        if not subject:
            raise ValueError("subject_key is required")

        existing = self._exit_intents.get(subject)
        if existing is not None and int(existing.priority) >= int(priority):
            return False

        self._exit_intents[subject] = ExitIntent(
            subject_key=subject,
            reason_code=str(reason_code or ""),
            priority=int(priority),
            scope_key=str(scope_key or ""),
            override_price=override_price,
            metadata=dict(metadata or {}),
        )
        return True

    def get_exit_intent(self, subject_key: str) -> Optional[ExitIntent]:
        return self._exit_intents.get(str(subject_key or ""))

    def get_all_exit_intents(self) -> List[ExitIntent]:
        return list(self._exit_intents.values())

    def drop_exit_intent(self, subject_key: str) -> None:
        self._exit_intents.pop(str(subject_key or ""), None)

    def upsert_exit_preempt_state(
        self,
        *,
        scope_key: str,
        reason_code: str,
        condition_active: bool = False,
        inflight: bool = False,
        pending: bool = False,
        pending_reason: str = "",
        updated_at: Optional[datetime] = None,
    ) -> ExitPreemptState:
        scope = str(scope_key or "")
        reason = str(reason_code or "")
        if not scope:
            raise ValueError("scope_key is required")
        if not reason:
            raise ValueError("reason_code is required")

        state = ExitPreemptState(
            reason_code=reason,
            condition_active=bool(condition_active),
            inflight=bool(inflight),
            pending=bool(pending),
            pending_reason=str(pending_reason or "") if pending else "",
            updated_at=updated_at,
        )
        self._exit_preempt_states.setdefault(scope, {})[reason] = state
        return state

    def get_exit_preempt_state(self, scope_key: str, reason_code: str) -> ExitPreemptState:
        scope = str(scope_key or "")
        reason = str(reason_code or "")
        if not scope or not reason:
            return ExitPreemptState.empty(reason)
        return self._exit_preempt_states.get(scope, {}).get(reason, ExitPreemptState.empty(reason))

    def clear_exit_preempt_state(self, scope_key: str, reason_code: str) -> None:
        scope = str(scope_key or "")
        reason = str(reason_code or "")
        reason_states = self._exit_preempt_states.get(scope)
        if reason_states is None:
            return
        reason_states.pop(reason, None)
        if not reason_states:
            self._exit_preempt_states.pop(scope, None)

    def get_scope_exit_preempt_summary(self, scope_key: str) -> Dict[str, Any]:
        scope = str(scope_key or "")
        reason_states = self._exit_preempt_states.get(scope, {})
        active_reason_codes = sorted(
            reason_code
            for reason_code, state in reason_states.items()
            if state.locked
        )
        return {
            "scope_key": scope,
            "locked": bool(active_reason_codes),
            "active_reason_codes": active_reason_codes,
            "states_by_reason": dict(reason_states),
        }

    def dump_execution_states(self) -> Dict[str, PositionExecutionState]:
        return dict(self._execution_states)

    def restore_execution_states(self, states: Dict[str, PositionExecutionState]) -> None:
        self._execution_states = dict(states)

    def begin_execution_intent(
        self,
        vt_symbol: str,
        intent_id: str,
        action: ExecutionAction,
        priority: ExecutionPriority = ExecutionPriority.OPEN_SIGNAL,
        requested_volume: int = 0,
        parent_combination_id: str = "",
        reason: str = "",
    ) -> PositionExecutionState:
        current = self._ensure_execution_state(vt_symbol)
        if current.phase.is_active:
            if priority <= current.priority:
                self._domain_events.append(
                    LegExecutionBlockedEvent(
                        scope="position",
                        identifier=vt_symbol,
                        intent_id=intent_id,
                        blocked_by_intent_id=current.intent_id,
                        requested_action=action.value,
                        current_phase=current.phase.value,
                        incoming_priority=int(priority),
                        active_priority=int(current.priority),
                        reason=reason,
                    )
                )
                raise RuntimeError(f"execution blocked for {vt_symbol}")
            self._domain_events.append(
                ExecutionPreemptedEvent(
                    scope="position",
                    identifier=vt_symbol,
                    previous_intent_id=current.intent_id,
                    new_intent_id=intent_id,
                    old_priority=int(current.priority),
                    new_priority=int(priority),
                    reason=reason,
                )
            )

        state = PositionExecutionState(
            vt_symbol=vt_symbol,
            intent_id=intent_id,
            action=action,
            phase=ExecutionPhase.RESERVED,
            priority=priority,
            requested_volume=requested_volume,
            parent_combination_id=parent_combination_id,
            reason=reason,
        )
        self._execution_states[vt_symbol] = state
        self._domain_events.append(
            ExecutionIntentStartedEvent(
                scope="position",
                identifier=vt_symbol,
                intent_id=intent_id,
                action=action.value,
                phase=state.phase.value,
                priority=int(priority),
            )
        )
        return state

    def request_cancel(
        self,
        vt_symbol: str,
        order_ids: Optional[Set[str]] = None,
        reason: str = "",
    ) -> None:
        state = self._ensure_execution_state(vt_symbol)
        state.cancel_requested_order_ids.update(set(order_ids or state.active_order_ids))
        self._set_phase(state, ExecutionPhase.CANCEL_PENDING, reason or "cancel_requested")

    def confirm_order_cancelled(self, vt_symbol: str, vt_orderid: str) -> None:
        state = self._ensure_execution_state(vt_symbol)
        state.active_order_ids.discard(vt_orderid)
        state.cancel_requested_order_ids.discard(vt_orderid)
        next_phase = ExecutionPhase.RETRY_PENDING if state.remaining_volume > 0 else ExecutionPhase.COMPLETED
        self._set_phase(state, next_phase, "order_cancelled")

    def complete_execution(self, vt_symbol: str, reason: str = "") -> None:
        state = self._ensure_execution_state(vt_symbol)
        state.active_order_ids.clear()
        state.cancel_requested_order_ids.clear()
        self._set_phase(state, ExecutionPhase.COMPLETED, reason or "complete_execution")

    def fail_execution(self, vt_symbol: str, reason: str = "") -> None:
        state = self._ensure_execution_state(vt_symbol)
        state.active_order_ids.clear()
        state.cancel_requested_order_ids.clear()
        self._set_phase(state, ExecutionPhase.FAILED, reason or "fail_execution")

    def preempt_execution(self, vt_symbol: str, new_intent_id: str, reason: str = "") -> None:
        state = self._ensure_execution_state(vt_symbol)
        state.preempted_by_intent_id = new_intent_id
        state.active_order_ids.clear()
        state.cancel_requested_order_ids.clear()
        self._set_phase(state, ExecutionPhase.PREEMPTED, reason or "preempt_execution")

    def has_pending_close(self, position: Position) -> bool:
        state = self._execution_states.get(position.vt_symbol)
        if state and state.action == ExecutionAction.CLOSE and state.phase.is_active:
            return True

        for order in self._pending_orders.values():
            if order.vt_symbol == position.vt_symbol and not order.is_open_order and order.is_active:
                return True
        return False

    def on_new_trading_day(self, current_date: date) -> None:
        if self._last_trading_date != current_date:
            self._daily_open_count_map.clear()
            self._global_daily_open_count = 0
            self._last_trading_date = current_date

    def record_open_usage(
        self,
        vt_symbol: str,
        volume: int,
        global_limit: int = 50,
        contract_limit: int = 2,
    ) -> None:
        self._global_daily_open_count += volume
        self._daily_open_count_map[vt_symbol] = self._daily_open_count_map.get(vt_symbol, 0) + volume

        if self._global_daily_open_count >= global_limit:
            self._domain_events.append(
                RiskLimitExceededEvent(
                    vt_symbol="GLOBAL",
                    limit_type="global",
                    current_volume=self._global_daily_open_count,
                    limit_volume=global_limit,
                )
            )

        if self._daily_open_count_map[vt_symbol] >= contract_limit:
            self._domain_events.append(
                RiskLimitExceededEvent(
                    vt_symbol=vt_symbol,
                    limit_type="contract",
                    current_volume=self._daily_open_count_map[vt_symbol],
                    limit_volume=contract_limit,
                )
            )

    def get_daily_open_volume(self, vt_symbol: str) -> int:
        return self._daily_open_count_map.get(vt_symbol, 0)

    def get_global_daily_open_volume(self) -> int:
        return self._global_daily_open_count

    def get_reserved_open_volume(self, vt_symbol: Optional[str] = None) -> int:
        total = 0
        for state_symbol, state in self._execution_states.items():
            if vt_symbol and state_symbol != vt_symbol:
                continue
            if state.action != ExecutionAction.OPEN or not state.phase.is_active:
                continue
            total += state.remaining_volume

        if total > 0:
            return total

        for order in self._pending_orders.values():
            if not order.is_open_order or not order.is_active:
                continue
            if vt_symbol and order.vt_symbol != vt_symbol:
                continue
            total += int(getattr(order, "remaining_volume", 0) or 0)
        return total

    def update_from_order(self, order_data: dict) -> None:
        vt_orderid = order_data.get("vt_orderid", "")
        vt_symbol = order_data.get("vt_symbol", "")
        status = str(order_data.get("status", "")).lower()
        traded = int(order_data.get("traded", 0) or 0)
        state = self._execution_states.get(vt_symbol)
        order = self._pending_orders.get(vt_orderid)
        if order is None:
            return

        status_mapping = {
            "submitting": OrderStatus.SUBMITTING,
            "nottraded": OrderStatus.NOTTRADED,
            "parttraded": OrderStatus.PARTTRADED,
            "alltraded": OrderStatus.ALLTRADED,
            "cancelled": OrderStatus.CANCELLED,
            "rejected": OrderStatus.REJECTED,
        }
        new_status = status_mapping.get(status)
        if new_status:
            order.update_status(new_status, traded)

        if state and vt_orderid in state.active_order_ids:
            if status == "submitting":
                self._set_phase(state, ExecutionPhase.SUBMITTING, "order_submitting")
            elif status == "nottraded":
                self._set_phase(state, ExecutionPhase.WORKING, "order_nottraded")
            elif status == "parttraded":
                self._set_phase(
                    state,
                    ExecutionPhase.PARTIAL_FILLED if traded else ExecutionPhase.WORKING,
                    "order_parttraded",
                )
            elif status == "cancelled":
                self.confirm_order_cancelled(vt_symbol, vt_orderid)
            elif status == "rejected":
                state.active_order_ids.discard(vt_orderid)
                self.fail_execution(vt_symbol, "order_rejected")
            elif status == "alltraded":
                state.active_order_ids.discard(vt_orderid)
                if state.filled_volume >= state.requested_volume or state.requested_volume <= traded:
                    self.complete_execution(vt_symbol, "order_alltraded")

        if order.is_finished:
            self._pending_orders.pop(vt_orderid, None)

    def update_from_trade(self, trade_data: dict) -> None:
        vt_symbol = trade_data.get("vt_symbol", "")
        volume = int(trade_data.get("volume", 0) or 0)
        offset = str(trade_data.get("offset", "")).lower()
        price = float(trade_data.get("price", 0.0) or 0.0)
        trade_time = trade_data.get("datetime", datetime.now())

        if vt_symbol not in self._managed_symbols:
            return

        position = self._positions.get(vt_symbol)
        if position is None:
            return

        state = self._execution_states.get(vt_symbol)

        if offset == "open":
            position.add_fill(volume, price, trade_time)
            self.record_open_usage(vt_symbol, volume)
            if state and state.action == ExecutionAction.OPEN:
                state.filled_volume += volume
                self._set_phase(
                    state,
                    ExecutionPhase.COMPLETED
                    if state.remaining_volume == 0 and not state.active_order_ids
                    else ExecutionPhase.PARTIAL_FILLED,
                    "trade_open",
                )
        else:
            was_closed = position.is_closed
            position.reduce_volume(volume, trade_time)
            if state and state.action == ExecutionAction.CLOSE:
                state.filled_volume += volume
                self._set_phase(
                    state,
                    ExecutionPhase.COMPLETED if position.is_closed else ExecutionPhase.PARTIAL_FILLED,
                    "trade_close",
                )
            if not was_closed and position.is_closed:
                self._emit_position_closed_event(position)

    def update_from_position(self, position_data: dict) -> None:
        vt_symbol = position_data.get("vt_symbol", "")
        actual_volume = int(position_data.get("volume", 0) or 0)

        if vt_symbol not in self._managed_symbols:
            return

        position = self._positions.get(vt_symbol)
        if position is None:
            return

        state = self._execution_states.get(vt_symbol)

        if actual_volume < position.volume:
            if state and state.action == ExecutionAction.CLOSE and state.phase.is_active:
                delta = position.volume - actual_volume
                position.reduce_volume(delta)
                if position.is_closed:
                    self.complete_execution(vt_symbol, "position_sync_closed")
                else:
                    self._set_phase(state, ExecutionPhase.PARTIAL_FILLED, "position_sync_close")
                return

            was_closed = position.is_closed
            manual_volume = position.volume - actual_volume
            position.mark_as_manually_closed(manual_volume)
            self._domain_events.append(
                ManualCloseDetectedEvent(
                    vt_symbol=vt_symbol,
                    volume=manual_volume,
                    timestamp=datetime.now(),
                )
            )
            if not was_closed and position.is_closed:
                self._emit_position_closed_event(position)

        elif actual_volume > position.volume:
            if state and state.action == ExecutionAction.OPEN and state.phase.is_active:
                delta = actual_volume - position.volume
                position.add_fill(delta, float(position_data.get("price", position.open_price or 0.0)), datetime.now())
                state.filled_volume += delta
                self._set_phase(
                    state,
                    ExecutionPhase.COMPLETED
                    if state.remaining_volume == 0 and not state.active_order_ids
                    else ExecutionPhase.PARTIAL_FILLED,
                    "position_sync_open",
                )
                return

            manual_volume = actual_volume - position.volume
            self._domain_events.append(
                ManualOpenDetectedEvent(
                    vt_symbol=vt_symbol,
                    volume=manual_volume,
                    timestamp=datetime.now(),
                )
            )

    def pop_domain_events(self) -> List[DomainEvent]:
        events = self._domain_events.copy()
        self._domain_events.clear()
        return events

    def has_pending_events(self) -> bool:
        return len(self._domain_events) > 0

    def is_managed(self, vt_symbol: str) -> bool:
        return vt_symbol in self._managed_symbols

    def clear(self) -> None:
        self._positions.clear()
        self._pending_orders.clear()
        self._execution_states.clear()
        self._exit_intents.clear()
        self._exit_preempt_states.clear()
        self._managed_symbols.clear()
        self._domain_events.clear()

    def __repr__(self) -> str:
        active_count = len(self.get_active_positions())
        pending_count = len(self._pending_orders)
        return f"PositionAggregate(active={active_count}, pending={pending_count})"

    def _ensure_execution_state(self, vt_symbol: str) -> PositionExecutionState:
        state = self._execution_states.get(vt_symbol)
        if state is None:
            state = PositionExecutionState(vt_symbol=vt_symbol)
            self._execution_states[vt_symbol] = state
        return state

    def _set_phase(
        self,
        state: PositionExecutionState,
        phase: ExecutionPhase,
        reason: str,
    ) -> None:
        old_phase = state.phase
        if old_phase == phase:
            state.mark_updated()
            return
        state.phase = phase
        state.mark_updated()
        self._domain_events.append(
            ExecutionPhaseChangedEvent(
                scope="position",
                identifier=state.vt_symbol,
                intent_id=state.intent_id,
                old_phase=old_phase.value,
                new_phase=phase.value,
                reason=reason,
            )
        )

    def _emit_position_closed_event(self, position: Position) -> None:
        self._domain_events.append(
            PositionClosedEvent(
                vt_symbol=position.vt_symbol,
                signal=position.signal,
                holding_seconds=position.holding_time or 0.0,
                pnl=0.0,
                timestamp=position.close_time or datetime.now(),
            )
        )
