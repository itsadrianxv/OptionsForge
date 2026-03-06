from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional, Set

from src.strategy.infrastructure.subscription.subscription_mode_engine import (
    MODE_ATM_BAND,
    MODE_CONFIGURED_CONTRACTS_ONLY,
    MODE_DOMINANT_NEARBY_K,
    MODE_DOMINANT_ONLY,
    MODE_INCLUDE_EXCLUDE_OVERLAY,
    MODE_LIQUIDITY_TOP_K_OPTIONS,
    MODE_POSITION_SAME_EXPIRY_CHAIN,
    MODE_POSITIONS_ONLY,
    MODE_POSITIONS_WITH_WINGS,
    MODE_PRODUCTS_DOMINANT_WITH_OPTIONS,
    MODE_SESSION_PROFILE,
    MODE_SIGNAL_DRIVEN_TEMPORARY,
    SubscriptionModeEngine,
    SubscriptionRuntimeContext,
)


@dataclass
class FakeExchange:
    value: str


@dataclass
class FakeOptionType:
    value: str


@dataclass
class FakeContract:
    vt_symbol: str
    symbol: str
    exchange: FakeExchange
    option_type: Optional[FakeOptionType] = None
    option_strike: float = 0.0
    underlying_symbol: str = ""


@dataclass
class FakeTick:
    last_price: float
    volume: float = 0.0
    open_interest: float = 0.0


def _build_contracts() -> List[FakeContract]:
    ex = FakeExchange("CFFEX")
    contracts: List[FakeContract] = [
        FakeContract("IF2605.CFFEX", "IF2605", ex),
        FakeContract("IF2606.CFFEX", "IF2606", ex),
        FakeContract("IF2607.CFFEX", "IF2607", ex),
    ]
    for strike in (4800, 4900, 5000, 5100, 5200):
        contracts.append(
            FakeContract(
                vt_symbol=f"IO2606-C-{strike}.CFFEX",
                symbol=f"IO2606-C-{strike}",
                exchange=ex,
                option_type=FakeOptionType("call"),
                option_strike=float(strike),
                underlying_symbol="IF2606",
            )
        )
        contracts.append(
            FakeContract(
                vt_symbol=f"IO2606-P-{strike}.CFFEX",
                symbol=f"IO2606-P-{strike}",
                exchange=ex,
                option_type=FakeOptionType("put"),
                option_strike=float(strike),
                underlying_symbol="IF2606",
            )
        )
    return contracts


def _build_context(
    *,
    now: Optional[datetime] = None,
    configured_products: Optional[List[str]] = None,
    configured_contracts: Optional[List[str]] = None,
    active_contracts_by_product: Optional[Dict[str, str]] = None,
    position_symbols: Optional[Set[str]] = None,
    pending_order_symbols: Optional[Set[str]] = None,
    signal_symbols: Optional[Set[str]] = None,
    existing_subscriptions: Optional[Set[str]] = None,
    ticks: Optional[Dict[str, FakeTick]] = None,
) -> SubscriptionRuntimeContext:
    contracts = _build_contracts()
    tick_map = ticks or {
        "IF2605.CFFEX": FakeTick(last_price=4990, volume=20, open_interest=200),
        "IF2606.CFFEX": FakeTick(last_price=5000, volume=500, open_interest=5000),
        "IF2607.CFFEX": FakeTick(last_price=5010, volume=40, open_interest=300),
    }
    for strike in (4800, 4900, 5000, 5100, 5200):
        tick_map.setdefault(f"IO2606-C-{strike}.CFFEX", FakeTick(last_price=30, volume=100 + strike, open_interest=50))
        tick_map.setdefault(f"IO2606-P-{strike}.CFFEX", FakeTick(last_price=30, volume=90 + strike, open_interest=40))

    return SubscriptionRuntimeContext(
        now=now or datetime(2026, 3, 6, 9, 30, 0),
        all_contracts=contracts,
        configured_products=configured_products or ["IF"],
        configured_contracts=configured_contracts or [],
        active_contracts_by_product=active_contracts_by_product or {"IF": "IF2606.CFFEX"},
        position_symbols=position_symbols or set(),
        pending_order_symbols=pending_order_symbols or set(),
        signal_symbols=signal_symbols or set(),
        existing_subscriptions=existing_subscriptions or set(),
        get_tick=lambda symbol: tick_map.get(symbol),
        get_last_price=lambda symbol: float(getattr(tick_map.get(symbol), "last_price", 0) or 0),
    )


def test_configured_contracts_only():
    engine = SubscriptionModeEngine(
        {
            "enabled": True,
            "enabled_modes": [MODE_CONFIGURED_CONTRACTS_ONLY],
            MODE_CONFIGURED_CONTRACTS_ONLY: {
                "vt_symbols": ["IF2606.CFFEX", "IO2606-C-5000.CFFEX"]
            },
        }
    )
    result = engine.resolve(_build_context())
    assert result.target_symbols == {"IF2606.CFFEX", "IO2606-C-5000.CFFEX"}


def test_products_dominant_with_options_atm_band():
    engine = SubscriptionModeEngine(
        {
            "enabled": True,
            "enabled_modes": [MODE_PRODUCTS_DOMINANT_WITH_OPTIONS],
            MODE_PRODUCTS_DOMINANT_WITH_OPTIONS: {
                "products": ["IF"],
                "option_scope": "atm_band",
                "band_n": 1,
                "expiry_policy": "same_as_dominant",
            },
        }
    )
    result = engine.resolve(_build_context())
    assert "IF2606.CFFEX" in result.target_symbols
    assert "IO2606-C-5000.CFFEX" in result.target_symbols
    assert "IO2606-P-4900.CFFEX" in result.target_symbols
    assert "IO2606-C-5200.CFFEX" not in result.target_symbols


def test_positions_only_with_wings():
    engine = SubscriptionModeEngine(
        {
            "enabled": True,
            "enabled_modes": [MODE_POSITIONS_ONLY, MODE_POSITIONS_WITH_WINGS],
            MODE_POSITIONS_ONLY: {"include_underlying": True, "include_pending_orders": True},
            MODE_POSITIONS_WITH_WINGS: {"wing_n": 1, "wing_side": "both", "include_call_put": False},
        }
    )
    context = _build_context(
        position_symbols={"IO2606-C-5000.CFFEX"},
        pending_order_symbols={"IO2606-P-5000.CFFEX"},
    )
    result = engine.resolve(context)
    assert "IF2606.CFFEX" in result.target_symbols
    assert "IO2606-C-4900.CFFEX" in result.target_symbols
    assert "IO2606-C-5100.CFFEX" in result.target_symbols
    assert "IO2606-P-4900.CFFEX" not in result.target_symbols


def test_dominant_nearby_k():
    engine = SubscriptionModeEngine(
        {
            "enabled": True,
            "enabled_modes": [MODE_DOMINANT_NEARBY_K],
            MODE_DOMINANT_NEARBY_K: {"products": ["IF"], "nearby_k": 1},
        }
    )
    result = engine.resolve(_build_context())
    assert result.target_symbols == {"IF2605.CFFEX", "IF2606.CFFEX", "IF2607.CFFEX"}


def test_position_same_expiry_chain():
    engine = SubscriptionModeEngine(
        {
            "enabled": True,
            "enabled_modes": [MODE_POSITION_SAME_EXPIRY_CHAIN],
            MODE_POSITION_SAME_EXPIRY_CHAIN: {"same_expiry_only": True, "include_call_put": True},
        }
    )
    result = engine.resolve(_build_context(position_symbols={"IO2606-P-5000.CFFEX"}))
    assert "IO2606-C-4800.CFFEX" in result.target_symbols
    assert "IO2606-P-5200.CFFEX" in result.target_symbols


def test_liquidity_top_k_options_filter():
    engine = SubscriptionModeEngine(
        {
            "enabled": True,
            "enabled_modes": [MODE_CONFIGURED_CONTRACTS_ONLY, MODE_LIQUIDITY_TOP_K_OPTIONS],
            MODE_CONFIGURED_CONTRACTS_ONLY: {
                "vt_symbols": [
                    "IO2606-C-4800.CFFEX",
                    "IO2606-C-4900.CFFEX",
                    "IO2606-C-5000.CFFEX",
                ]
            },
            MODE_LIQUIDITY_TOP_K_OPTIONS: {
                "enabled": True,
                "k": 2,
                "metric": "volume",
                "min_volume": 0,
                "min_oi": 0,
            },
        }
    )
    ticks = {
        "IF2606.CFFEX": FakeTick(last_price=5000, volume=500, open_interest=5000),
        "IO2606-C-4800.CFFEX": FakeTick(last_price=50, volume=50, open_interest=10),
        "IO2606-C-4900.CFFEX": FakeTick(last_price=40, volume=80, open_interest=10),
        "IO2606-C-5000.CFFEX": FakeTick(last_price=30, volume=100, open_interest=10),
    }
    result = engine.resolve(_build_context(ticks=ticks))
    assert result.target_symbols == {"IO2606-C-4900.CFFEX", "IO2606-C-5000.CFFEX"}


def test_overlay_and_must_keep_priority():
    engine = SubscriptionModeEngine(
        {
            "enabled": True,
            "enabled_modes": [MODE_CONFIGURED_CONTRACTS_ONLY, MODE_INCLUDE_EXCLUDE_OVERLAY],
            MODE_CONFIGURED_CONTRACTS_ONLY: {"vt_symbols": ["IF2606.CFFEX"]},
            MODE_INCLUDE_EXCLUDE_OVERLAY: {
                "force_include": [],
                "force_exclude": ["IF2606.CFFEX", "IO2606-C-5000.CFFEX"],
                "allow_exclude_must_keep": False,
            },
        }
    )
    result = engine.resolve(_build_context(position_symbols={"IO2606-C-5000.CFFEX"}))
    assert "IF2606.CFFEX" not in result.target_symbols
    assert "IO2606-C-5000.CFFEX" in result.target_symbols


def test_session_profile_switch_mode():
    engine = SubscriptionModeEngine(
        {
            "enabled": True,
            "enabled_modes": [MODE_SESSION_PROFILE],
            MODE_SESSION_PROFILE: {
                "default_modes": [MODE_CONFIGURED_CONTRACTS_ONLY],
                "profiles": [
                    {"name": "open", "start": "08:00", "end": "10:00", "modes": [MODE_DOMINANT_ONLY]}
                ],
            },
            MODE_CONFIGURED_CONTRACTS_ONLY: {"vt_symbols": ["IO2606-C-5000.CFFEX"]},
            MODE_DOMINANT_ONLY: {"products": ["IF"]},
        }
    )
    result = engine.resolve(_build_context(now=datetime(2026, 3, 6, 9, 0, 0)))
    assert result.target_symbols == {"IF2606.CFFEX"}


def test_signal_driven_temporary():
    engine = SubscriptionModeEngine(
        {
            "enabled": True,
            "enabled_modes": [MODE_SIGNAL_DRIVEN_TEMPORARY, MODE_ATM_BAND],
            MODE_SIGNAL_DRIVEN_TEMPORARY: {
                "include_underlying": True,
                "option_band_n": 1,
                "max_temp_symbols": 20,
            },
        }
    )
    result = engine.resolve(_build_context(signal_symbols={"IF2606.CFFEX"}))
    assert "IF2606.CFFEX" in result.target_symbols
    assert "IO2606-C-5000.CFFEX" in result.target_symbols
    assert "IO2606-P-5100.CFFEX" in result.target_symbols
