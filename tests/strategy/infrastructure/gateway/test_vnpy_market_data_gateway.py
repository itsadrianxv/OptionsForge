from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from src.strategy.infrastructure.gateway.vnpy_market_data_gateway import (
    VnpyMarketDataGateway,
)


def test_get_tick_in_backtesting_sets_pre_settlement_price_default() -> None:
    context = SimpleNamespace(
        strategy_name="test_strategy",
        backtesting=True,
        last_bars={
            "IF2506.CFFEX": SimpleNamespace(close_price=4123.5, volume=42),
        },
    )

    with patch(
        "src.strategy.infrastructure.gateway.vnpy_gateway_adapter.setup_strategy_logger",
        return_value=MagicMock(),
    ):
        gateway = VnpyMarketDataGateway(context)

    tick = gateway.get_tick("IF2506.CFFEX")

    assert tick is not None
    assert tick.last_price == 4123.5
    assert tick.pre_settlement_price == 0.0
