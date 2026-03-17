from __future__ import annotations

import sys
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import MagicMock

from src.strategy.domain.aggregate.instrument_manager import InstrumentManager
from src.strategy.domain.aggregate.position_aggregate import PositionAggregate
from src.strategy.domain.value_object.market.option_contract import OptionContract
from src.strategy.domain.value_object.signal import (
    IndicatorComputationResult,
    OptionSelectionPreference,
    SignalDecision,
)


sys.modules.setdefault("vnpy", MagicMock())
sys.modules.setdefault("vnpy.event", MagicMock())
sys.modules.setdefault("vnpy.event.engine", MagicMock())
sys.modules.setdefault("vnpy.trader", MagicMock())
sys.modules.setdefault("vnpy.trader.constant", MagicMock())
sys.modules.setdefault("vnpy.trader.engine", MagicMock())
sys.modules.setdefault("vnpy.trader.event", MagicMock())
sys.modules.setdefault("vnpy.trader.object", MagicMock())
sys.modules.setdefault("vnpy_portfoliostrategy", MagicMock())
sys.modules.setdefault("vnpy_portfoliostrategy.utility", MagicMock())

from src.strategy.application.market_workflow import MarketWorkflow  # noqa: E402


class _IndicatorService:
    def calculate_bar(self, instrument, bar, context=None):
        instrument.indicators["demo"] = {"value": 1}
        return IndicatorComputationResult(
            indicator_key="demo",
            updated_indicator_keys=["demo"],
            values={"value": 1},
            summary="demo indicator",
        )


class _SignalService:
    def check_open_signal(self, instrument, context=None):
        return SignalDecision(
            action="open",
            signal_name="demo_open",
            rationale="unit test signal",
            selection_preference=OptionSelectionPreference(option_type="call", strike_level=1),
        )

    def check_close_signal(self, instrument, position, context=None):
        return None


class _MarketGateway:
    def __init__(self):
        self._contracts = [
            SimpleNamespace(
                vt_symbol="IO2506-C-3800.CFFEX",
                option_type="CALL",
                option_underlying="IF2506",
                option_strike=3800,
                exchange=SimpleNamespace(value="CFFEX"),
                size=100,
                pricetick=0.2,
            )
        ]

    def get_all_contracts(self):
        return self._contracts

    def get_tick(self, vt_symbol):
        return SimpleNamespace(
            vt_symbol=vt_symbol,
            bid_price_1=10.0,
            bid_volume_1=20,
            ask_price_1=10.2,
            ask_volume_1=20,
            last_price=10.1,
            volume=100,
            open_interest=500,
            datetime=datetime(2026, 1, 2, 10, 0, 0),
        )

    def get_contract(self, vt_symbol):
        return self._contracts[0]


def test_market_workflow_emits_decision_trace_for_open_pipeline() -> None:
    captured_traces: list[dict] = []
    option_chain_loader = MagicMock()
    contract_selector = MagicMock()
    greeks_enricher = MagicMock()
    pricing_enricher = MagicMock()
    sizing_evaluator = MagicMock()
    execution_planner = MagicMock()
    execution_scheduler = MagicMock()
    rebalance_planner = MagicMock()
    selected_contract = OptionContract(
        vt_symbol="IO2506-C-3800.CFFEX",
        underlying_symbol="IF2506.CFFEX",
        option_type="call",
        strike_price=3800,
        expiry_date="2025-06-20",
        diff1=0.01,
        bid_price=10.0,
        bid_volume=20,
        ask_price=10.2,
        ask_volume=20,
        days_to_expiry=30,
    )

    entry = SimpleNamespace()
    entry.bar_pipeline = None
    entry.target_aggregate = InstrumentManager()
    entry.position_aggregate = PositionAggregate()
    entry.market_gateway = _MarketGateway()
    entry.indicator_service = _IndicatorService()
    entry.signal_service = _SignalService()
    entry.option_selector_service = None
    entry.position_sizing_service = None
    entry.greeks_calculator = None
    entry.pricing_engine = None
    entry.runtime = SimpleNamespace(
        observability=SimpleNamespace(trace_sinks=[captured_traces.append]),
        state=SimpleNamespace(snapshot_sinks=[]),
        open_pipeline=SimpleNamespace(
            option_chain_loader=option_chain_loader,
            contract_selector=contract_selector,
            greeks_enricher=greeks_enricher,
            pricing_enricher=pricing_enricher,
            sizing_evaluator=sizing_evaluator,
            execution_planner=execution_planner,
            execution_scheduler=execution_scheduler,
        ),
        portfolio=SimpleNamespace(rebalance_planner=rebalance_planner),
    )
    entry.observability_config = {"emit_noop_decisions": False}
    entry.service_activation = {
        "option_chain": False,
        "option_selector": False,
        "pricing_engine": False,
        "greeks_calculator": False,
        "position_sizing": False,
        "decision_observability": True,
    }
    entry.decision_journal = []
    entry.decision_journal_limit = 20
    entry.logger = MagicMock()
    entry.current_dt = datetime(2026, 1, 2, 10, 0, 0)
    entry._record_snapshot = lambda: None
    entry._register_signal_temporary_symbol = lambda vt_symbol: None
    entry.last_decision_trace = None
    entry.risk_thresholds = MagicMock()

    option_chain_loader.side_effect = lambda vt_symbol, instrument, bar_data: workflow._build_option_chain_snapshot_from_gateway(
        vt_symbol,
        instrument.latest_close,
        bar_data["datetime"],
    )
    contract_selector.return_value = selected_contract
    greeks_enricher.return_value = SimpleNamespace(delta=0.2, gamma=0.01, theta=-0.05, vega=0.3)
    pricing_enricher.return_value = {"theoretical_price": 10.3, "pricing_model": "stub"}
    sizing_evaluator.return_value = {"passed": True, "final_volume": 2, "summary": "runtime sizing"}
    execution_planner.return_value = {"planned_action": "open", "suggested_volume": 2}
    execution_scheduler.return_value = {
        "planned_action": "open",
        "suggested_volume": 2,
        "scheduled": True,
    }
    rebalance_planner.return_value = {"action": "hedge", "reason": "delta drift"}

    workflow = MarketWorkflow(entry)
    bar = SimpleNamespace(
        datetime=datetime(2026, 1, 2, 10, 0, 0),
        open_price=100.0,
        high_price=101.0,
        low_price=99.0,
        close_price=100.5,
        volume=1000,
    )

    workflow.process_bars({"IF2506.CFFEX": bar})

    assert entry.last_decision_trace is not None
    assert captured_traces
    assert any(stage["stage"] == "selection" for stage in captured_traces[-1]["stages"])
    assert any(stage["stage"] == "pricing" and stage["status"] == "ok" for stage in captured_traces[-1]["stages"])
    assert any(stage["stage"] == "sizing" and stage["status"] == "ok" for stage in captured_traces[-1]["stages"])
    assert any(stage["stage"] == "execution_plan" and stage["payload"].get("scheduled") is True for stage in captured_traces[-1]["stages"])
    assert any(stage["stage"] == "rebalance_plan" for stage in captured_traces[-1]["stages"])
    option_chain_loader.assert_called_once()
    contract_selector.assert_called_once()
    greeks_enricher.assert_called_once()
    pricing_enricher.assert_called_once()
    sizing_evaluator.assert_called_once()
    execution_planner.assert_called_once()
    execution_scheduler.assert_called_once()
    rebalance_planner.assert_called_once()
