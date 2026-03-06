"""
组合领域服务编排单元测试

验证上层直接编排调用组合领域服务时，子服务异常不被吞没并按调用顺序传播。

_Requirements: 6.4_
"""
from datetime import datetime
from typing import Dict, Optional
from unittest.mock import MagicMock

import pytest

from src.strategy.domain.domain_service.combination.combination_greeks_calculator import (
    CombinationGreeksCalculator,
)
from src.strategy.domain.domain_service.combination.combination_pnl_calculator import (
    CombinationPnLCalculator,
)
from src.strategy.domain.domain_service.combination.combination_risk_checker import (
    CombinationRiskChecker,
)
from src.strategy.domain.entity.combination import Combination
from src.strategy.domain.value_object.combination import (
    CombinationEvaluation,
    CombinationGreeks,
    CombinationPnL,
    CombinationStatus,
    CombinationType,
    Leg,
)
from src.strategy.domain.value_object.pricing.greeks import GreeksResult


def _evaluate_combination(
    greeks_calculator: CombinationGreeksCalculator,
    pnl_calculator: CombinationPnLCalculator,
    risk_checker: CombinationRiskChecker,
    combination: Combination,
    greeks_map: Dict[str, GreeksResult],
    current_prices: Dict[str, float],
    multiplier: float,
    realized_pnl_map: Optional[Dict[str, float]] = None,
) -> CombinationEvaluation:
    """上层直接编排组合评估流程。"""
    greeks = greeks_calculator.calculate(combination, greeks_map, multiplier)
    pnl = pnl_calculator.calculate(
        combination, current_prices, multiplier, realized_pnl_map
    )
    risk_result = risk_checker.check(greeks)
    return CombinationEvaluation(greeks=greeks, pnl=pnl, risk_result=risk_result)


def _make_combination() -> Combination:
    """构建一个简单的测试 Combination。"""
    return Combination(
        combination_id="test-service-orchestration",
        combination_type=CombinationType.CUSTOM,
        underlying_vt_symbol="TEST.UND",
        legs=[
            Leg(
                vt_symbol="OPT1.TEST",
                option_type="call",
                strike_price=3000.0,
                expiry_date="20250901",
                direction="long",
                volume=1,
                open_price=100.0,
            ),
        ],
        status=CombinationStatus.ACTIVE,
        create_time=datetime(2025, 1, 1),
    )


class TestServiceOrchestrationExceptionPropagation:
    """验证上层直接编排时异常传播。"""

    def test_greeks_calculator_exception_propagates(self):
        greeks_calc = MagicMock(spec=CombinationGreeksCalculator)
        greeks_calc.calculate.side_effect = ValueError("Greeks 计算失败")
        pnl_calc, risk_checker = MagicMock(spec=CombinationPnLCalculator), MagicMock(
            spec=CombinationRiskChecker
        )
        combination = _make_combination()

        with pytest.raises(ValueError, match="Greeks 计算失败"):
            _evaluate_combination(
                greeks_calc,
                pnl_calc,
                risk_checker,
                combination,
                greeks_map={"OPT1.TEST": GreeksResult()},
                current_prices={"OPT1.TEST": 110.0},
                multiplier=10.0,
            )

    def test_pnl_calculator_exception_propagates(self):
        greeks_calc = MagicMock(spec=CombinationGreeksCalculator)
        greeks_calc.calculate.return_value = CombinationGreeks()

        pnl_calc = MagicMock(spec=CombinationPnLCalculator)
        pnl_calc.calculate.side_effect = RuntimeError("PnL 计算失败")
        risk_checker = MagicMock(spec=CombinationRiskChecker)

        combination = _make_combination()

        with pytest.raises(RuntimeError, match="PnL 计算失败"):
            _evaluate_combination(
                greeks_calc,
                pnl_calc,
                risk_checker,
                combination,
                greeks_map={"OPT1.TEST": GreeksResult()},
                current_prices={"OPT1.TEST": 110.0},
                multiplier=10.0,
            )

    def test_risk_checker_exception_propagates(self):
        greeks_calc = MagicMock(spec=CombinationGreeksCalculator)
        greeks_calc.calculate.return_value = CombinationGreeks()

        pnl_calc = MagicMock(spec=CombinationPnLCalculator)
        pnl_calc.calculate.return_value = CombinationPnL(total_unrealized_pnl=0.0)

        risk_checker = MagicMock(spec=CombinationRiskChecker)
        risk_checker.check.side_effect = TypeError("风控检查失败")

        combination = _make_combination()

        with pytest.raises(TypeError, match="风控检查失败"):
            _evaluate_combination(
                greeks_calc,
                pnl_calc,
                risk_checker,
                combination,
                greeks_map={"OPT1.TEST": GreeksResult()},
                current_prices={"OPT1.TEST": 110.0},
                multiplier=10.0,
            )

    def test_greeks_exception_prevents_pnl_and_risk(self):
        greeks_calc = MagicMock(spec=CombinationGreeksCalculator)
        greeks_calc.calculate.side_effect = ValueError("Greeks 异常")

        pnl_calc = MagicMock(spec=CombinationPnLCalculator)
        risk_checker = MagicMock(spec=CombinationRiskChecker)
        combination = _make_combination()

        with pytest.raises(ValueError):
            _evaluate_combination(
                greeks_calc,
                pnl_calc,
                risk_checker,
                combination,
                greeks_map={},
                current_prices={},
                multiplier=10.0,
            )

        pnl_calc.calculate.assert_not_called()
        risk_checker.check.assert_not_called()

    def test_pnl_exception_prevents_risk_check(self):
        greeks_calc = MagicMock(spec=CombinationGreeksCalculator)
        greeks_calc.calculate.return_value = CombinationGreeks()

        pnl_calc = MagicMock(spec=CombinationPnLCalculator)
        pnl_calc.calculate.side_effect = RuntimeError("PnL 异常")

        risk_checker = MagicMock(spec=CombinationRiskChecker)
        combination = _make_combination()

        with pytest.raises(RuntimeError):
            _evaluate_combination(
                greeks_calc,
                pnl_calc,
                risk_checker,
                combination,
                greeks_map={},
                current_prices={},
                multiplier=10.0,
            )

        risk_checker.check.assert_not_called()
