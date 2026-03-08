"""统一的期权链数据模型。"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _normalize_option_type(raw: Any) -> Optional[str]:
    text = str(getattr(raw, "value", raw) or "").strip().lower()
    if text in {"call", "认购", "c"}:
        return "call"
    if text in {"put", "认沽", "p"}:
        return "put"
    return None


def _extract_underlying_ref(contract: Any) -> str:
    for attr in (
        "underlying_vt_symbol",
        "underlying_symbol",
        "option_underlying",
        "underlying",
    ):
        value = getattr(contract, attr, None)
        if value:
            return str(value)
    return ""


def _matches_underlying(contract: Any, underlying_vt_symbol: str) -> bool:
    if not underlying_vt_symbol:
        return False
    underlying_ref = _extract_underlying_ref(contract)
    if not underlying_ref:
        return False
    if underlying_ref == underlying_vt_symbol:
        return True

    symbol_part = underlying_vt_symbol.split(".", 1)[0]
    exchange_part = underlying_vt_symbol.split(".", 1)[1] if "." in underlying_vt_symbol else ""

    return bool(
        underlying_ref == symbol_part
        or (symbol_part and exchange_part and underlying_ref == f"{symbol_part}.{exchange_part}")
        or (symbol_part and underlying_ref.startswith(symbol_part))
    )


def _extract_expiry(contract: Any) -> str:
    for attr in ("option_expiry", "expiry_date", "expire_date", "option_expiry_date"):
        value = getattr(contract, attr, None)
        if value:
            if isinstance(value, datetime):
                return value.strftime("%Y-%m-%d")
            return str(value)
    return ""


def _calc_days_to_expiry(expiry_text: str, as_of: datetime) -> int:
    if not expiry_text:
        return 0
    for fmt in ("%Y-%m-%d", "%Y%m%d"):
        try:
            expiry = datetime.strptime(expiry_text, fmt)
            return max((expiry.date() - as_of.date()).days, 0)
        except ValueError:
            continue
    return 0


@dataclass(frozen=True)
class OptionContractSnapshot:
    vt_symbol: str
    underlying_vt_symbol: str
    option_type: str
    strike_price: float
    expiry_date: str
    days_to_expiry: int
    pricetick: float = 0.0
    size: int = 0
    exchange: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class OptionQuoteSnapshot:
    vt_symbol: str
    bid_price: float
    bid_volume: int
    ask_price: float
    ask_volume: int
    last_price: float
    volume: float
    open_interest: float
    implied_volatility: Optional[float] = None
    quote_dt: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class OptionChainEntry:
    contract: OptionContractSnapshot
    quote: OptionQuoteSnapshot

    def to_record(self, underlying_price: float) -> Dict[str, Any]:
        strike = self.contract.strike_price
        option_type = self.contract.option_type
        if option_type == "call":
            diff1 = max((strike - underlying_price) / underlying_price, 0.0) if underlying_price > 0 else 0.0
        else:
            diff1 = max((underlying_price - strike) / underlying_price, 0.0) if underlying_price > 0 else 0.0

        return {
            "vt_symbol": self.contract.vt_symbol,
            "underlying_symbol": self.contract.underlying_vt_symbol,
            "option_type": self.contract.option_type,
            "strike_price": self.contract.strike_price,
            "expiry_date": self.contract.expiry_date,
            "days_to_expiry": self.contract.days_to_expiry,
            "bid_price": self.quote.bid_price,
            "bid_volume": self.quote.bid_volume,
            "ask_price": self.quote.ask_price,
            "ask_volume": self.quote.ask_volume,
            "last_price": self.quote.last_price,
            "volume": self.quote.volume,
            "open_interest": self.quote.open_interest,
            "implied_volatility": self.quote.implied_volatility,
            "diff1": diff1,
        }


@dataclass
class OptionChainSnapshot:
    underlying_vt_symbol: str
    underlying_price: float
    as_of: datetime
    entries: List[OptionChainEntry] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def is_empty(self) -> bool:
        return not self.entries

    def to_selector_frame(self):
        import pandas as pd

        if not self.entries:
            return pd.DataFrame()
        return pd.DataFrame([entry.to_record(self.underlying_price) for entry in self.entries])

    @classmethod
    def from_contracts(
        cls,
        underlying_vt_symbol: str,
        underlying_price: float,
        contracts: List[Any],
        get_tick: Optional[Callable[[str], Any]] = None,
        as_of: Optional[datetime] = None,
    ) -> "OptionChainSnapshot":
        as_of = as_of or datetime.now()
        entries: List[OptionChainEntry] = []

        for contract in contracts or []:
            option_type = _normalize_option_type(getattr(contract, "option_type", None))
            if option_type is None:
                continue
            if not _matches_underlying(contract, underlying_vt_symbol):
                continue

            vt_symbol = str(getattr(contract, "vt_symbol", "") or "")
            if not vt_symbol:
                continue

            strike_raw = (
                getattr(contract, "option_strike", None)
                or getattr(contract, "strike_price", None)
                or getattr(contract, "strike", None)
                or getattr(contract, "option_strike_price", None)
            )
            strike = _safe_float(strike_raw)
            if strike <= 0:
                continue

            expiry_date = _extract_expiry(contract)
            quote = get_tick(vt_symbol) if callable(get_tick) else None
            quote_dt = getattr(quote, "datetime", None)
            iv = getattr(quote, "implied_volatility", None)

            entries.append(
                OptionChainEntry(
                    contract=OptionContractSnapshot(
                        vt_symbol=vt_symbol,
                        underlying_vt_symbol=underlying_vt_symbol,
                        option_type=option_type,
                        strike_price=strike,
                        expiry_date=expiry_date,
                        days_to_expiry=_calc_days_to_expiry(expiry_date, as_of),
                        pricetick=_safe_float(getattr(contract, "pricetick", 0.0)),
                        size=_safe_int(getattr(contract, "size", 0)),
                        exchange=str(getattr(getattr(contract, "exchange", None), "value", "") or ""),
                    ),
                    quote=OptionQuoteSnapshot(
                        vt_symbol=vt_symbol,
                        bid_price=_safe_float(getattr(quote, "bid_price_1", 0.0)),
                        bid_volume=_safe_int(getattr(quote, "bid_volume_1", 0)),
                        ask_price=_safe_float(getattr(quote, "ask_price_1", 0.0)),
                        ask_volume=_safe_int(getattr(quote, "ask_volume_1", 0)),
                        last_price=_safe_float(getattr(quote, "last_price", 0.0)),
                        volume=_safe_float(getattr(quote, "volume", 0.0)),
                        open_interest=_safe_float(getattr(quote, "open_interest", 0.0)),
                        implied_volatility=_safe_float(iv, 0.0) if iv is not None else None,
                        quote_dt=quote_dt if isinstance(quote_dt, datetime) else None,
                    ),
                )
            )

        return cls(
            underlying_vt_symbol=underlying_vt_symbol,
            underlying_price=underlying_price,
            as_of=as_of,
            entries=entries,
        )
