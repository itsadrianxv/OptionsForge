from __future__ import annotations

import logging
from types import SimpleNamespace

import pytest
import vnpy_ctp.gateway.ctp_gateway as ctp_gateway_module
from vnpy.trader.constant import Exchange

from src.main.bootstrap.ctp_tick_patch import (
    ORIGINAL_METHOD_ATTR,
    PATCH_SENTINEL_ATTR,
    patch_ctp_pre_settlement_price,
)


def _restore_vendor_handler() -> None:
    ctp_md_api_cls = ctp_gateway_module.CtpMdApi
    original_handler = getattr(ctp_md_api_cls, ORIGINAL_METHOD_ATTR, None)
    if original_handler is not None:
        ctp_md_api_cls.onRtnDepthMarketData = original_handler
        delattr(ctp_md_api_cls, ORIGINAL_METHOD_ATTR)

    if hasattr(ctp_md_api_cls, PATCH_SENTINEL_ATTR):
        delattr(ctp_md_api_cls, PATCH_SENTINEL_ATTR)


@pytest.fixture(autouse=True)
def restore_ctp_md_api_patch() -> None:
    _restore_vendor_handler()
    yield
    _restore_vendor_handler()


def test_patch_ctp_pre_settlement_price_is_idempotent(caplog) -> None:
    ctp_md_api_cls = ctp_gateway_module.CtpMdApi

    with caplog.at_level(logging.INFO, logger="src.main.bootstrap.ctp_tick_patch"):
        patch_ctp_pre_settlement_price()
        patched_handler = ctp_md_api_cls.onRtnDepthMarketData
        patch_ctp_pre_settlement_price()

    assert getattr(ctp_md_api_cls, PATCH_SENTINEL_ATTR, False) is True
    assert getattr(ctp_md_api_cls, ORIGINAL_METHOD_ATTR) is not None
    assert ctp_md_api_cls.onRtnDepthMarketData is patched_handler
    assert caplog.text.count("pre_settlement_price") == 1


def test_patch_ctp_pre_settlement_price_populates_tick_field(monkeypatch) -> None:
    patch_ctp_pre_settlement_price()

    ticks = []
    symbol = "rb2505"
    contract = SimpleNamespace(exchange=Exchange.SHFE, name="rb 主力")
    gateway = SimpleNamespace(on_tick=ticks.append)
    api = SimpleNamespace(
        current_date="20260316",
        gateway_name="CTP",
        gateway=gateway,
    )
    data = {
        "InstrumentID": symbol,
        "UpdateTime": "09:31:15",
        "UpdateMillisec": 500,
        "ActionDay": "20260316",
        "Volume": 123,
        "Turnover": 4567.0,
        "OpenInterest": 8910,
        "LastPrice": 3456.0,
        "UpperLimitPrice": 3800.0,
        "LowerLimitPrice": 3000.0,
        "OpenPrice": 3400.0,
        "HighestPrice": 3470.0,
        "LowestPrice": 3390.0,
        "PreClosePrice": 3388.0,
        "PreSettlementPrice": ctp_gateway_module.MAX_FLOAT,
        "BidPrice1": 3455.0,
        "AskPrice1": 3456.0,
        "BidVolume1": 10,
        "AskVolume1": 12,
        "BidVolume2": 0,
        "AskVolume2": 0,
    }

    monkeypatch.setitem(ctp_gateway_module.symbol_contract_map, symbol, contract)

    ctp_gateway_module.CtpMdApi.onRtnDepthMarketData(api, data)

    assert len(ticks) == 1
    tick = ticks[0]
    assert tick.pre_settlement_price == 0.0
    assert tick.last_price == ctp_gateway_module.adjust_price(data["LastPrice"])
    assert tick.pre_close == ctp_gateway_module.adjust_price(data["PreClosePrice"])
