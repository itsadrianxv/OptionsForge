"""
ctp_tick_patch.py - CTP 行情 Tick 运行时补丁

职责:
在网关加载前为 vnpy_ctp 的 CtpMdApi 注入 pre_settlement_price，
避免修改 site-packages，并保证重复调用幂等。
"""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

PATCH_SENTINEL_ATTR = "_codex_pre_settlement_price_patch_applied"
ORIGINAL_METHOD_ATTR = "_codex_original_on_rtn_depth_market_data"


def patch_ctp_pre_settlement_price(
    patch_logger: logging.Logger | None = None,
) -> None:
    """
    为 vnpy_ctp 的 Tick 映射补充 pre_settlement_price 字段。

    该补丁只在当前进程内生效，并且支持重复调用幂等。
    """
    import vnpy_ctp.gateway.ctp_gateway as ctp_gateway_module

    ctp_md_api_cls = ctp_gateway_module.CtpMdApi
    if getattr(ctp_md_api_cls, PATCH_SENTINEL_ATTR, False):
        return

    original_handler = ctp_md_api_cls.onRtnDepthMarketData
    adjust_price = ctp_gateway_module.adjust_price
    symbol_contract_map = ctp_gateway_module.symbol_contract_map
    china_tz = ctp_gateway_module.CHINA_TZ
    dt_parser = ctp_gateway_module.datetime
    exchange_enum = ctp_gateway_module.Exchange
    tick_type = ctp_gateway_module.TickData

    def patched_on_rtn_depth_market_data(self, data: dict) -> None:
        """行情数据推送。"""
        if not data["UpdateTime"]:
            return

        symbol: str = data["InstrumentID"]
        contract = symbol_contract_map.get(symbol, None)
        if not contract:
            return

        if not data["ActionDay"] or contract.exchange == exchange_enum.DCE:
            date_str: str = self.current_date
        else:
            date_str = data["ActionDay"]

        timestamp: str = f"{date_str} {data['UpdateTime']}.{data['UpdateMillisec']}"
        dt = dt_parser.strptime(timestamp, "%Y%m%d %H:%M:%S.%f")
        dt = dt.replace(tzinfo=china_tz)

        tick = tick_type(
            symbol=symbol,
            exchange=contract.exchange,
            datetime=dt,
            name=contract.name,
            volume=data["Volume"],
            turnover=data["Turnover"],
            open_interest=data["OpenInterest"],
            last_price=adjust_price(data["LastPrice"]),
            limit_up=data["UpperLimitPrice"],
            limit_down=data["LowerLimitPrice"],
            open_price=adjust_price(data["OpenPrice"]),
            high_price=adjust_price(data["HighestPrice"]),
            low_price=adjust_price(data["LowestPrice"]),
            pre_close=adjust_price(data["PreClosePrice"]),
            bid_price_1=adjust_price(data["BidPrice1"]),
            ask_price_1=adjust_price(data["AskPrice1"]),
            bid_volume_1=data["BidVolume1"],
            ask_volume_1=data["AskVolume1"],
            gateway_name=self.gateway_name,
        )
        tick.pre_settlement_price = adjust_price(data["PreSettlementPrice"])

        if data["BidVolume2"] or data["AskVolume2"]:
            tick.bid_price_2 = adjust_price(data["BidPrice2"])
            tick.bid_price_3 = adjust_price(data["BidPrice3"])
            tick.bid_price_4 = adjust_price(data["BidPrice4"])
            tick.bid_price_5 = adjust_price(data["BidPrice5"])

            tick.ask_price_2 = adjust_price(data["AskPrice2"])
            tick.ask_price_3 = adjust_price(data["AskPrice3"])
            tick.ask_price_4 = adjust_price(data["AskPrice4"])
            tick.ask_price_5 = adjust_price(data["AskPrice5"])

            tick.bid_volume_2 = data["BidVolume2"]
            tick.bid_volume_3 = data["BidVolume3"]
            tick.bid_volume_4 = data["BidVolume4"]
            tick.bid_volume_5 = data["BidVolume5"]

            tick.ask_volume_2 = data["AskVolume2"]
            tick.ask_volume_3 = data["AskVolume3"]
            tick.ask_volume_4 = data["AskVolume4"]
            tick.ask_volume_5 = data["AskVolume5"]

        self.gateway.on_tick(tick)

    setattr(ctp_md_api_cls, ORIGINAL_METHOD_ATTR, original_handler)
    ctp_md_api_cls.onRtnDepthMarketData = patched_on_rtn_depth_market_data
    setattr(ctp_md_api_cls, PATCH_SENTINEL_ATTR, True)

    active_logger = patch_logger or logger
    active_logger.info(
        "CTP 行情补丁已启用，Tick 将注入 pre_settlement_price"
    )
