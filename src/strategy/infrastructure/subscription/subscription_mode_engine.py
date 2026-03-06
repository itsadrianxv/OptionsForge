"""
subscription_mode_engine.py - 可组合订阅模式引擎

负责根据订阅配置和运行时上下文，计算目标订阅集合。
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, time
import math
import re
from typing import Any, Callable, DefaultDict, Dict, Iterable, List, Optional, Sequence, Set

MODE_CONFIGURED_CONTRACTS_ONLY = "configured_contracts_only"
MODE_PRODUCTS_DOMINANT_WITH_OPTIONS = "products_dominant_with_options"
MODE_POSITIONS_ONLY = "positions_only"
MODE_POSITIONS_WITH_WINGS = "positions_with_wings"
MODE_DOMINANT_ONLY = "dominant_only"
MODE_DOMINANT_NEARBY_K = "dominant_nearby_k"
MODE_ATM_BAND = "atm_band"
MODE_POSITION_SAME_EXPIRY_CHAIN = "position_same_expiry_chain"
MODE_LIQUIDITY_TOP_K_OPTIONS = "liquidity_top_k_options"
MODE_SIGNAL_DRIVEN_TEMPORARY = "signal_driven_temporary"
MODE_SESSION_PROFILE = "session_profile"
MODE_INCLUDE_EXCLUDE_OVERLAY = "include_exclude_overlay"

ALL_MODES: Set[str] = {
    MODE_CONFIGURED_CONTRACTS_ONLY,
    MODE_PRODUCTS_DOMINANT_WITH_OPTIONS,
    MODE_POSITIONS_ONLY,
    MODE_POSITIONS_WITH_WINGS,
    MODE_DOMINANT_ONLY,
    MODE_DOMINANT_NEARBY_K,
    MODE_ATM_BAND,
    MODE_POSITION_SAME_EXPIRY_CHAIN,
    MODE_LIQUIDITY_TOP_K_OPTIONS,
    MODE_SIGNAL_DRIVEN_TEMPORARY,
    MODE_SESSION_PROFILE,
    MODE_INCLUDE_EXCLUDE_OVERLAY,
}

MODE_PRIORITY: Dict[str, int] = {
    MODE_POSITIONS_ONLY: 100,
    MODE_POSITIONS_WITH_WINGS: 120,
    MODE_PRODUCTS_DOMINANT_WITH_OPTIONS: 200,
    MODE_ATM_BAND: 220,
    MODE_CONFIGURED_CONTRACTS_ONLY: 300,
    MODE_DOMINANT_ONLY: 320,
    MODE_DOMINANT_NEARBY_K: 340,
    MODE_POSITION_SAME_EXPIRY_CHAIN: 360,
    MODE_SIGNAL_DRIVEN_TEMPORARY: 380,
    MODE_LIQUIDITY_TOP_K_OPTIONS: 800,
    MODE_SESSION_PROFILE: 850,
    MODE_INCLUDE_EXCLUDE_OVERLAY: 900,
}


@dataclass(frozen=True)
class OptionMeta:
    vt_symbol: str
    symbol: str
    product: str
    underlying_vt_symbol: str
    strike: float
    option_type: str  # call | put
    expiry: str


@dataclass(frozen=True)
class FutureMeta:
    vt_symbol: str
    symbol: str
    product: str
    contract_month: int


@dataclass
class ContractIndex:
    by_vt_symbol: Dict[str, Any] = field(default_factory=dict)
    future_meta_by_vt: Dict[str, FutureMeta] = field(default_factory=dict)
    option_meta_by_vt: Dict[str, OptionMeta] = field(default_factory=dict)
    futures_by_product: DefaultDict[str, List[str]] = field(default_factory=lambda: defaultdict(list))
    options_by_underlying: DefaultDict[str, List[str]] = field(default_factory=lambda: defaultdict(list))

    @property
    def all_option_symbols(self) -> Set[str]:
        return set(self.option_meta_by_vt.keys())

    @staticmethod
    def build(all_contracts: Sequence[Any]) -> "ContractIndex":
        index = ContractIndex()

        future_symbol_to_vts: DefaultDict[str, List[str]] = defaultdict(list)

        # pass 1: futures
        for contract in all_contracts:
            vt_symbol = _get_text(contract, "vt_symbol")
            if not vt_symbol:
                continue
            symbol = _get_text(contract, "symbol")
            index.by_vt_symbol[vt_symbol] = contract

            if _is_option_contract(contract):
                continue

            product = _extract_product(symbol)
            contract_month = _extract_contract_month(symbol)
            index.future_meta_by_vt[vt_symbol] = FutureMeta(
                vt_symbol=vt_symbol,
                symbol=symbol,
                product=product,
                contract_month=contract_month,
            )
            if product:
                index.futures_by_product[product].append(vt_symbol)
            if symbol:
                future_symbol_to_vts[symbol].append(vt_symbol)

        # pass 2: options
        for contract in all_contracts:
            if not _is_option_contract(contract):
                continue

            vt_symbol = _get_text(contract, "vt_symbol")
            if not vt_symbol:
                continue

            symbol = _get_text(contract, "symbol")
            product = _extract_product(symbol)
            option_type = _normalize_option_type(contract, symbol, vt_symbol)
            if option_type is None:
                continue

            strike = _extract_strike(contract, symbol)
            if strike is None:
                continue

            underlying_raw = (
                _get_text(contract, "underlying_symbol")
                or _get_text(contract, "option_underlying")
                or _get_text(contract, "underlying")
                or _get_text(contract, "underlying_vt_symbol")
            )
            underlying_vt = _normalize_underlying_vt_symbol(
                underlying_raw=underlying_raw,
                option_symbol=symbol,
                existing_vts=index.by_vt_symbol,
                future_symbol_to_vts=future_symbol_to_vts,
            )
            if not underlying_vt:
                continue

            expiry = _extract_expiry(contract, vt_symbol)
            meta = OptionMeta(
                vt_symbol=vt_symbol,
                symbol=symbol,
                product=product,
                underlying_vt_symbol=underlying_vt,
                strike=float(strike),
                option_type=option_type,
                expiry=expiry,
            )
            index.option_meta_by_vt[vt_symbol] = meta
            index.options_by_underlying[underlying_vt].append(vt_symbol)
            index.by_vt_symbol[vt_symbol] = contract

        # keep deterministic order
        for product, items in list(index.futures_by_product.items()):
            index.futures_by_product[product] = sorted(
                items,
                key=lambda vt: (
                    index.future_meta_by_vt.get(vt, FutureMeta(vt, "", "", 0)).contract_month,
                    vt,
                ),
            )
        for underlying, items in list(index.options_by_underlying.items()):
            index.options_by_underlying[underlying] = sorted(items)

        return index


@dataclass
class SubscriptionRuntimeContext:
    now: datetime
    all_contracts: Sequence[Any]
    configured_products: Sequence[str]
    configured_contracts: Sequence[str]
    active_contracts_by_product: Dict[str, str]
    position_symbols: Set[str]
    pending_order_symbols: Set[str]
    signal_symbols: Set[str]
    existing_subscriptions: Set[str]
    get_tick: Callable[[str], Any]
    get_last_price: Callable[[str], float]


@dataclass
class SubscriptionPlanResult:
    enabled: bool
    effective_modes: List[str]
    target_symbols: Set[str]
    must_keep_symbols: Set[str]
    force_include_symbols: Set[str]
    force_exclude_symbols: Set[str]
    mode_symbols: Dict[str, Set[str]]
    warnings: List[str]
    priority_map: Dict[str, int]


class SubscriptionModeEngine:
    """
    订阅模式集合计算引擎。

    仅负责计算目标集合，不直接执行订阅/退订。
    """

    def __init__(self, config: Optional[Dict[str, Any]]) -> None:
        self.config: Dict[str, Any] = dict(config or {})

    def resolve(self, ctx: SubscriptionRuntimeContext) -> SubscriptionPlanResult:
        enabled = bool(self.config.get("enabled", True))
        if not enabled:
            return SubscriptionPlanResult(
                enabled=False,
                effective_modes=[],
                target_symbols=set(ctx.existing_subscriptions),
                must_keep_symbols=set(),
                force_include_symbols=set(),
                force_exclude_symbols=set(),
                mode_symbols={},
                warnings=[],
                priority_map={},
            )

        index = ContractIndex.build(ctx.all_contracts)
        warnings: List[str] = []
        mode_symbols: Dict[str, Set[str]] = {}
        priority_map: Dict[str, int] = {}

        symbols: Set[str] = set()

        must_keep = self._build_must_keep_set(ctx)
        for symbol in must_keep:
            priority_map[symbol] = min(priority_map.get(symbol, 10_000), 0)

        effective_modes = self._resolve_effective_modes(ctx.now)

        # Source + Expander
        for mode in effective_modes:
            produced = self._run_mode(mode=mode, ctx=ctx, index=index, warnings=warnings)
            if not produced:
                mode_symbols[mode] = set()
                continue
            mode_symbols[mode] = set(produced)
            symbols.update(produced)
            mode_priority = MODE_PRIORITY.get(mode, 9_999)
            for symbol in produced:
                priority_map[symbol] = min(priority_map.get(symbol, 10_000), mode_priority)

        # Filter
        if MODE_LIQUIDITY_TOP_K_OPTIONS in effective_modes:
            symbols = self._apply_liquidity_top_k_filter(
                symbols=symbols,
                must_keep=must_keep,
                force_include=set(),
                index=index,
                ctx=ctx,
                warnings=warnings,
            )

        overlay_cfg = self.config.get(MODE_INCLUDE_EXCLUDE_OVERLAY, {})
        force_include = set(_ensure_string_list(overlay_cfg.get("force_include", [])))
        force_exclude = set(_ensure_string_list(overlay_cfg.get("force_exclude", [])))
        allow_exclude_must_keep = bool(overlay_cfg.get("allow_exclude_must_keep", False))

        for symbol in force_include:
            priority_map[symbol] = min(priority_map.get(symbol, 10_000), 10)

        final_symbols = set(symbols) | force_include

        for symbol in force_exclude:
            if symbol in must_keep and not allow_exclude_must_keep:
                continue
            final_symbols.discard(symbol)

        if allow_exclude_must_keep:
            final_symbols |= (must_keep - force_exclude)
        else:
            final_symbols |= must_keep

        for symbol in must_keep:
            priority_map[symbol] = min(priority_map.get(symbol, 10_000), 0)

        final_symbols = self._apply_max_symbols_cap(
            symbols=final_symbols,
            must_keep=must_keep,
            force_include=force_include,
            priority_map=priority_map,
            ctx=ctx,
            index=index,
        )

        return SubscriptionPlanResult(
            enabled=True,
            effective_modes=effective_modes,
            target_symbols=final_symbols,
            must_keep_symbols=must_keep,
            force_include_symbols=force_include,
            force_exclude_symbols=force_exclude,
            mode_symbols=mode_symbols,
            warnings=warnings,
            priority_map=priority_map,
        )

    def _resolve_effective_modes(self, now: datetime) -> List[str]:
        base_modes = [m for m in _ensure_string_list(self.config.get("enabled_modes", [])) if m in ALL_MODES]
        modes_set = set(base_modes)

        if MODE_SESSION_PROFILE in modes_set:
            profile_modes = self._resolve_session_profile_modes(now)
            modes_set.update(profile_modes)

        # include_exclude_overlay 允许仅靠 section 生效
        if MODE_INCLUDE_EXCLUDE_OVERLAY not in modes_set and MODE_INCLUDE_EXCLUDE_OVERLAY in self.config:
            overlay_cfg = self.config.get(MODE_INCLUDE_EXCLUDE_OVERLAY, {})
            if overlay_cfg.get("force_include") or overlay_cfg.get("force_exclude"):
                modes_set.add(MODE_INCLUDE_EXCLUDE_OVERLAY)

        return sorted(modes_set, key=lambda m: MODE_PRIORITY.get(m, 9_999))

    def _resolve_session_profile_modes(self, now: datetime) -> List[str]:
        cfg = self.config.get(MODE_SESSION_PROFILE, {}) or {}
        default_modes = [m for m in _ensure_string_list(cfg.get("default_modes", [])) if m in ALL_MODES]
        profiles = cfg.get("profiles", []) or []
        now_t = now.time()

        for p in profiles:
            if not isinstance(p, dict):
                continue
            start = _parse_hhmm(p.get("start", "00:00"))
            end = _parse_hhmm(p.get("end", "23:59"))
            if _time_in_range(now_t, start, end):
                return [m for m in _ensure_string_list(p.get("modes", [])) if m in ALL_MODES]
        return default_modes

    def _build_must_keep_set(self, ctx: SubscriptionRuntimeContext) -> Set[str]:
        must_keep: Set[str] = set()
        if bool(self.config.get("keep_position_protection", True)):
            must_keep.update(ctx.position_symbols)
        if bool(self.config.get("keep_active_order_protection", True)):
            must_keep.update(ctx.pending_order_symbols)
        return {s for s in must_keep if s}

    def _run_mode(
        self,
        mode: str,
        ctx: SubscriptionRuntimeContext,
        index: ContractIndex,
        warnings: List[str],
    ) -> Set[str]:
        if mode == MODE_CONFIGURED_CONTRACTS_ONLY:
            return self._mode_configured_contracts_only(ctx, index)
        if mode == MODE_PRODUCTS_DOMINANT_WITH_OPTIONS:
            return self._mode_products_dominant_with_options(ctx, index, warnings)
        if mode == MODE_POSITIONS_ONLY:
            return self._mode_positions_only(ctx, index)
        if mode == MODE_POSITIONS_WITH_WINGS:
            return self._mode_positions_with_wings(ctx, index)
        if mode == MODE_DOMINANT_ONLY:
            return self._mode_dominant_only(ctx, index, warnings)
        if mode == MODE_DOMINANT_NEARBY_K:
            return self._mode_dominant_nearby_k(ctx, index, warnings)
        if mode == MODE_ATM_BAND:
            return self._mode_atm_band(ctx, index, warnings)
        if mode == MODE_POSITION_SAME_EXPIRY_CHAIN:
            return self._mode_position_same_expiry_chain(ctx, index)
        if mode == MODE_SIGNAL_DRIVEN_TEMPORARY:
            return self._mode_signal_driven_temporary(ctx, index)
        if mode in (MODE_LIQUIDITY_TOP_K_OPTIONS, MODE_INCLUDE_EXCLUDE_OVERLAY, MODE_SESSION_PROFILE):
            return set()
        return set()

    def _mode_configured_contracts_only(self, ctx: SubscriptionRuntimeContext, index: ContractIndex) -> Set[str]:
        cfg = self.config.get(MODE_CONFIGURED_CONTRACTS_ONLY, {}) or {}
        from_cfg = set(_ensure_string_list(cfg.get("vt_symbols", [])))
        symbols = from_cfg or set(_ensure_string_list(ctx.configured_contracts))
        return {s for s in symbols if s in index.by_vt_symbol}

    def _mode_products_dominant_with_options(
        self,
        ctx: SubscriptionRuntimeContext,
        index: ContractIndex,
        warnings: List[str],
    ) -> Set[str]:
        cfg = self.config.get(MODE_PRODUCTS_DOMINANT_WITH_OPTIONS, {}) or {}
        products = _normalize_products(cfg.get("products", [])) or _normalize_products(ctx.configured_products)
        option_scope = str(cfg.get("option_scope", "none")).strip().lower()
        band_n = int(cfg.get("band_n", 4) or 4)
        expiry_policy = str(cfg.get("expiry_policy", "same_as_dominant")).strip().lower()

        result: Set[str] = set()

        for product in products:
            dominant = self._get_dominant_future(product, ctx, index)
            if not dominant:
                warnings.append(f"未找到品种 {product} 的主力合约")
                continue
            result.add(dominant)

            if option_scope == "none":
                continue
            if option_scope == "atm_band":
                dominant_expiry = _extract_contract_expiry_from_vt(dominant)
                option_symbols = self._select_atm_band_options(
                    underlying_vt_symbol=dominant,
                    band_n=band_n,
                    include_call_put=True,
                    index=index,
                    ctx=ctx,
                )
                if expiry_policy == "same_as_dominant" and dominant_expiry:
                    option_symbols = {
                        s for s in option_symbols
                        if index.option_meta_by_vt.get(s, OptionMeta("", "", "", "", 0.0, "call", "")).expiry == dominant_expiry
                    }
                result.update(option_symbols)
                continue
            if option_scope == "same_expiry_chain":
                dominant_expiry = _extract_contract_expiry_from_vt(dominant)
                if not dominant_expiry:
                    continue
                for vt in index.options_by_underlying.get(dominant, []):
                    meta = index.option_meta_by_vt.get(vt)
                    if meta and meta.expiry == dominant_expiry:
                        result.add(vt)

        return result

    def _mode_positions_only(self, ctx: SubscriptionRuntimeContext, index: ContractIndex) -> Set[str]:
        cfg = self.config.get(MODE_POSITIONS_ONLY, {}) or {}
        include_underlying = bool(cfg.get("include_underlying", True))
        include_pending = bool(cfg.get("include_pending_orders", True))

        result: Set[str] = set(ctx.position_symbols)
        if include_pending:
            result.update(ctx.pending_order_symbols)

        if include_underlying:
            for symbol in list(result):
                if symbol in index.option_meta_by_vt:
                    result.add(index.option_meta_by_vt[symbol].underlying_vt_symbol)

        return {s for s in result if s in index.by_vt_symbol}

    def _mode_positions_with_wings(self, ctx: SubscriptionRuntimeContext, index: ContractIndex) -> Set[str]:
        cfg = self.config.get(MODE_POSITIONS_WITH_WINGS, {}) or {}
        wing_n = max(0, int(cfg.get("wing_n", 2) or 2))
        wing_side = str(cfg.get("wing_side", "both")).strip().lower()
        include_call_put = bool(cfg.get("include_call_put", True))

        result: Set[str] = set()

        for pos_symbol in ctx.position_symbols:
            pos_meta = index.option_meta_by_vt.get(pos_symbol)
            if not pos_meta:
                continue

            option_vts = index.options_by_underlying.get(pos_meta.underlying_vt_symbol, [])
            scoped = [
                index.option_meta_by_vt[vt]
                for vt in option_vts
                if index.option_meta_by_vt.get(vt) and index.option_meta_by_vt[vt].expiry == pos_meta.expiry
            ]
            if not scoped:
                continue

            strikes = sorted({m.strike for m in scoped})
            if not strikes:
                continue

            center_idx = min(range(len(strikes)), key=lambda i: abs(strikes[i] - pos_meta.strike))
            selected_strikes: Set[float] = {strikes[center_idx]}

            for step in range(1, wing_n + 1):
                lower_idx = center_idx - step
                upper_idx = center_idx + step
                if wing_side in ("both", "itm") and _is_itm_for_option_type(pos_meta.option_type, direction="lower"):
                    if lower_idx >= 0:
                        selected_strikes.add(strikes[lower_idx])
                elif wing_side in ("both", "otm") and lower_idx >= 0:
                    selected_strikes.add(strikes[lower_idx])

                if wing_side in ("both", "itm") and _is_itm_for_option_type(pos_meta.option_type, direction="upper"):
                    if upper_idx < len(strikes):
                        selected_strikes.add(strikes[upper_idx])
                elif wing_side in ("both", "otm") and upper_idx < len(strikes):
                    selected_strikes.add(strikes[upper_idx])

            for meta in scoped:
                if meta.strike not in selected_strikes:
                    continue
                if include_call_put:
                    result.add(meta.vt_symbol)
                else:
                    if meta.option_type == pos_meta.option_type:
                        result.add(meta.vt_symbol)

        return result

    def _mode_dominant_only(
        self,
        ctx: SubscriptionRuntimeContext,
        index: ContractIndex,
        warnings: List[str],
    ) -> Set[str]:
        cfg = self.config.get(MODE_DOMINANT_ONLY, {}) or {}
        products = _normalize_products(cfg.get("products", [])) or _normalize_products(ctx.configured_products)
        result: Set[str] = set()
        for product in products:
            dominant = self._get_dominant_future(product, ctx, index)
            if dominant:
                result.add(dominant)
            else:
                warnings.append(f"dominant_only 未找到 {product} 的主力")
        return result

    def _mode_dominant_nearby_k(
        self,
        ctx: SubscriptionRuntimeContext,
        index: ContractIndex,
        warnings: List[str],
    ) -> Set[str]:
        cfg = self.config.get(MODE_DOMINANT_NEARBY_K, {}) or {}
        products = _normalize_products(cfg.get("products", [])) or _normalize_products(ctx.configured_products)
        nearby_k = max(0, int(cfg.get("nearby_k", 1) or 1))
        result: Set[str] = set()

        for product in products:
            dominant = self._get_dominant_future(product, ctx, index)
            if not dominant:
                warnings.append(f"dominant_nearby_k 未找到 {product} 的主力")
                continue
            result.add(dominant)

            futures = index.futures_by_product.get(product, [])
            if dominant not in futures:
                continue
            dominant_idx = futures.index(dominant)
            lo = max(0, dominant_idx - nearby_k)
            hi = min(len(futures) - 1, dominant_idx + nearby_k)
            result.update(futures[lo : hi + 1])

        return result

    def _mode_atm_band(
        self,
        ctx: SubscriptionRuntimeContext,
        index: ContractIndex,
        warnings: List[str],
    ) -> Set[str]:
        cfg = self.config.get(MODE_ATM_BAND, {}) or {}
        underlyings_from = str(cfg.get("underlyings_from", "dominant")).strip().lower()
        band_n = max(0, int(cfg.get("band_n", 4) or 4))
        include_call_put = bool(cfg.get("include_call_put", True))

        underlyings: Set[str] = set()
        if underlyings_from == "positions":
            for symbol in ctx.position_symbols:
                if symbol in index.option_meta_by_vt:
                    underlyings.add(index.option_meta_by_vt[symbol].underlying_vt_symbol)
                elif symbol in index.future_meta_by_vt:
                    underlyings.add(symbol)
        elif underlyings_from == "config":
            underlyings.update(_ensure_string_list(ctx.configured_contracts))
        else:
            products = _normalize_products(ctx.configured_products)
            for product in products:
                dominant = self._get_dominant_future(product, ctx, index)
                if dominant:
                    underlyings.add(dominant)
                else:
                    warnings.append(f"atm_band 未找到 {product} 的主力")

        result: Set[str] = set()
        for underlying in underlyings:
            result.update(
                self._select_atm_band_options(
                    underlying_vt_symbol=underlying,
                    band_n=band_n,
                    include_call_put=include_call_put,
                    index=index,
                    ctx=ctx,
                )
            )
        return result

    def _mode_position_same_expiry_chain(self, ctx: SubscriptionRuntimeContext, index: ContractIndex) -> Set[str]:
        cfg = self.config.get(MODE_POSITION_SAME_EXPIRY_CHAIN, {}) or {}
        include_call_put = bool(cfg.get("include_call_put", True))
        same_expiry_only = bool(cfg.get("same_expiry_only", True))
        result: Set[str] = set()

        for symbol in ctx.position_symbols:
            pos_meta = index.option_meta_by_vt.get(symbol)
            if not pos_meta:
                continue
            for option_symbol in index.options_by_underlying.get(pos_meta.underlying_vt_symbol, []):
                option_meta = index.option_meta_by_vt.get(option_symbol)
                if option_meta is None:
                    continue
                if same_expiry_only and option_meta.expiry != pos_meta.expiry:
                    continue
                if not include_call_put and option_meta.option_type != pos_meta.option_type:
                    continue
                result.add(option_symbol)
        return result

    def _mode_signal_driven_temporary(self, ctx: SubscriptionRuntimeContext, index: ContractIndex) -> Set[str]:
        cfg = self.config.get(MODE_SIGNAL_DRIVEN_TEMPORARY, {}) or {}
        include_underlying = bool(cfg.get("include_underlying", True))
        option_band_n = max(0, int(cfg.get("option_band_n", 2) or 2))
        max_temp_symbols = max(1, int(cfg.get("max_temp_symbols", 50) or 50))

        raw_symbols = list(sorted(s for s in ctx.signal_symbols if s in index.by_vt_symbol))
        if len(raw_symbols) > max_temp_symbols:
            raw_symbols = raw_symbols[:max_temp_symbols]
        result: Set[str] = set(raw_symbols)

        if include_underlying:
            extras: Set[str] = set()
            for symbol in list(result):
                if symbol in index.option_meta_by_vt:
                    extras.add(index.option_meta_by_vt[symbol].underlying_vt_symbol)
                if symbol in index.future_meta_by_vt and option_band_n > 0:
                    extras.update(
                        self._select_atm_band_options(
                            underlying_vt_symbol=symbol,
                            band_n=option_band_n,
                            include_call_put=True,
                            index=index,
                            ctx=ctx,
                        )
                    )
            result.update(extras)

        return result

    def _apply_liquidity_top_k_filter(
        self,
        symbols: Set[str],
        must_keep: Set[str],
        force_include: Set[str],
        index: ContractIndex,
        ctx: SubscriptionRuntimeContext,
        warnings: List[str],
    ) -> Set[str]:
        cfg = self.config.get(MODE_LIQUIDITY_TOP_K_OPTIONS, {}) or {}
        if not bool(cfg.get("enabled", False)):
            return symbols

        k = max(1, int(cfg.get("k", 80) or 80))
        metric = str(cfg.get("metric", "score")).strip().lower()
        min_volume = float(cfg.get("min_volume", 0) or 0)
        min_oi = float(cfg.get("min_oi", 0) or 0)

        option_candidates = [s for s in symbols if s in index.all_option_symbols]
        if len(option_candidates) <= k:
            return symbols

        scored: List[tuple[str, float]] = []
        for symbol in option_candidates:
            tick = ctx.get_tick(symbol)
            volume = _safe_float(getattr(tick, "volume", 0) if tick else 0)
            oi = _safe_float(getattr(tick, "open_interest", 0) if tick else 0)
            if volume < min_volume or oi < min_oi:
                continue
            score = _calc_liquidity_score(metric, volume, oi)
            scored.append((symbol, score))

        scored.sort(key=lambda x: (x[1], x[0]), reverse=True)
        keep_options = {symbol for symbol, _ in scored[:k]}

        removed_count = 0
        result = set(symbols)
        for symbol in option_candidates:
            if symbol in keep_options:
                continue
            if symbol in must_keep or symbol in force_include:
                continue
            if symbol in result:
                result.remove(symbol)
                removed_count += 1

        if removed_count > 0:
            warnings.append(f"liquidity_top_k_options 已裁剪 {removed_count} 个期权订阅")

        return result

    def _apply_max_symbols_cap(
        self,
        symbols: Set[str],
        must_keep: Set[str],
        force_include: Set[str],
        priority_map: Dict[str, int],
        ctx: SubscriptionRuntimeContext,
        index: ContractIndex,
    ) -> Set[str]:
        max_symbols = int(self.config.get("max_symbols", 0) or 0)
        if max_symbols <= 0 or len(symbols) <= max_symbols:
            return symbols

        allow_overflow = bool(self.config.get("allow_overflow_for_must_keep", True))
        protected = set(must_keep) | set(force_include)
        protected = {s for s in protected if s in symbols}

        others = list(symbols - protected)
        others.sort(
            key=lambda s: (
                priority_map.get(s, 10_000),
                -_calc_liquidity_score(
                    "score",
                    _safe_float(getattr(ctx.get_tick(s), "volume", 0) if ctx.get_tick(s) else 0),
                    _safe_float(getattr(ctx.get_tick(s), "open_interest", 0) if ctx.get_tick(s) else 0),
                ),
                s,
            )
        )

        if allow_overflow and len(protected) >= max_symbols:
            return protected

        keep: Set[str] = set()
        if allow_overflow:
            keep.update(protected)
            remaining = max(max_symbols - len(keep), 0)
            keep.update(others[:remaining])
            return keep

        ordered_all = list(symbols)
        ordered_all.sort(
            key=lambda s: (
                priority_map.get(s, 10_000),
                -_calc_liquidity_score(
                    "score",
                    _safe_float(getattr(ctx.get_tick(s), "volume", 0) if ctx.get_tick(s) else 0),
                    _safe_float(getattr(ctx.get_tick(s), "open_interest", 0) if ctx.get_tick(s) else 0),
                ),
                s,
            )
        )
        return set(ordered_all[:max_symbols])

    def _get_dominant_future(
        self,
        product: str,
        ctx: SubscriptionRuntimeContext,
        index: ContractIndex,
    ) -> Optional[str]:
        product = (product or "").upper()
        active = (ctx.active_contracts_by_product or {}).get(product)
        if active and active in index.by_vt_symbol:
            return active

        futures = index.futures_by_product.get(product, [])
        if not futures:
            return None

        best_symbol = None
        best_score = -1.0
        for vt_symbol in futures:
            tick = ctx.get_tick(vt_symbol)
            volume = _safe_float(getattr(tick, "volume", 0) if tick else 0)
            oi = _safe_float(getattr(tick, "open_interest", 0) if tick else 0)
            score = _calc_liquidity_score("score", volume, oi)
            if score > best_score:
                best_score = score
                best_symbol = vt_symbol

        if best_symbol:
            return best_symbol

        return futures[0]

    def _select_atm_band_options(
        self,
        underlying_vt_symbol: str,
        band_n: int,
        include_call_put: bool,
        index: ContractIndex,
        ctx: SubscriptionRuntimeContext,
    ) -> Set[str]:
        options = index.options_by_underlying.get(underlying_vt_symbol, [])
        if not options:
            return set()

        metas = [index.option_meta_by_vt[s] for s in options if s in index.option_meta_by_vt]
        if not metas:
            return set()

        underlying_price = ctx.get_last_price(underlying_vt_symbol)
        if underlying_price <= 0:
            # price unavailable: keep nearest strike around median
            strikes = sorted({m.strike for m in metas})
            if not strikes:
                return set()
            center_idx = len(strikes) // 2
        else:
            strikes = sorted({m.strike for m in metas})
            center_idx = min(range(len(strikes)), key=lambda i: abs(strikes[i] - underlying_price))

        lo = max(0, center_idx - band_n)
        hi = min(len(strikes) - 1, center_idx + band_n)
        selected_strikes = set(strikes[lo : hi + 1])

        selected: Set[str] = set()
        for meta in metas:
            if meta.strike not in selected_strikes:
                continue
            if include_call_put:
                selected.add(meta.vt_symbol)
            else:
                # include_call_put=false 时优先保留 call
                if meta.option_type == "call":
                    selected.add(meta.vt_symbol)

        return selected


def _is_option_contract(contract: Any) -> bool:
    option_type = getattr(contract, "option_type", None)
    if option_type is not None:
        return True
    for key in ("option_strike", "strike_price", "strike", "option_strike_price"):
        raw = getattr(contract, key, None)
        if raw not in (None, "", 0, 0.0):
            return True
    symbol = _get_text(contract, "symbol")
    return bool(re.search(r"-(C|P)-", symbol, flags=re.IGNORECASE))


def _extract_product(symbol: str) -> str:
    m = re.match(r"^([A-Za-z]+)", symbol or "")
    return m.group(1).upper() if m else ""


def _extract_contract_month(symbol: str) -> int:
    m = re.search(r"(\d{3,4})$", symbol or "")
    if not m:
        return 0
    try:
        return int(m.group(1))
    except ValueError:
        return 0


def _extract_contract_expiry_from_vt(vt_symbol: str) -> str:
    return _extract_expiry_from_symbol(vt_symbol)


def _extract_expiry(contract: Any, vt_symbol: str) -> str:
    raw = getattr(contract, "option_expiry", None)
    if isinstance(raw, datetime):
        return raw.strftime("%y%m")
    text = str(raw or "").strip()
    if text:
        m = re.search(r"(\d{4})", text)
        if m:
            return m.group(1)
    return _extract_expiry_from_symbol(vt_symbol)


def _extract_strike(contract: Any, symbol: str) -> Optional[float]:
    for key in ("option_strike", "strike_price", "strike", "option_strike_price"):
        raw = getattr(contract, key, None)
        if raw in (None, ""):
            continue
        value = _safe_float(raw)
        if value > 0:
            return value

    m = re.search(r"-(?:C|P)-([0-9]+(?:\.[0-9]+)?)", symbol or "", flags=re.IGNORECASE)
    if m:
        return _safe_float(m.group(1))

    m2 = re.search(r"(?:C|P)([0-9]+(?:\.[0-9]+)?)$", symbol or "", flags=re.IGNORECASE)
    if m2:
        return _safe_float(m2.group(1))

    return None


def _normalize_option_type(contract: Any, symbol: str, vt_symbol: str) -> Optional[str]:
    raw = getattr(contract, "option_type", None)
    if raw is not None:
        value = getattr(raw, "value", raw)
        text = str(value).strip().lower()
        if value == 1 or text in ("call", "c", "optiontype.call"):
            return "call"
        if value == 2 or text in ("put", "p", "optiontype.put"):
            return "put"

    for text in (symbol, vt_symbol):
        m = re.search(r"-(C|P)-", text or "", flags=re.IGNORECASE)
        if m:
            return "call" if m.group(1).upper() == "C" else "put"

    return None


def _normalize_underlying_vt_symbol(
    underlying_raw: str,
    option_symbol: str,
    existing_vts: Dict[str, Any],
    future_symbol_to_vts: DefaultDict[str, List[str]],
) -> Optional[str]:
    if underlying_raw:
        text = str(underlying_raw).strip()
        if "." in text and text in existing_vts:
            return text
        if text in future_symbol_to_vts and future_symbol_to_vts[text]:
            return future_symbol_to_vts[text][0]
        if "." in text:
            symbol_only = text.split(".")[0]
            if symbol_only in future_symbol_to_vts and future_symbol_to_vts[symbol_only]:
                return future_symbol_to_vts[symbol_only][0]

    # fallback: IF->IO 等映射反推
    m = re.match(r"^([A-Za-z]+)(\d{3,4})", option_symbol or "")
    if not m:
        return None
    option_product = m.group(1).upper()
    suffix = m.group(2)
    reverse_map = {"IO": "IF", "MO": "IM", "HO": "IH"}
    future_product = reverse_map.get(option_product)
    if not future_product:
        return None
    future_symbol = f"{future_product}{suffix}"
    vts = future_symbol_to_vts.get(future_symbol, [])
    return vts[0] if vts else None


def _calc_liquidity_score(metric: str, volume: float, oi: float) -> float:
    metric = (metric or "score").lower()
    if metric == "volume":
        return volume
    if metric == "oi":
        return oi
    # score
    return 0.6 * volume + 0.4 * oi


def _safe_float(value: Any) -> float:
    try:
        v = float(value)
    except (TypeError, ValueError):
        return 0.0
    if not math.isfinite(v):
        return 0.0
    return v


def _get_text(contract: Any, key: str) -> str:
    value = getattr(contract, key, "")
    return str(value or "").strip()


def _parse_hhmm(value: str) -> time:
    text = str(value or "00:00").strip()
    try:
        hour, minute = text.split(":")
        return time(hour=int(hour), minute=int(minute))
    except Exception:
        return time(0, 0)


def _time_in_range(now_t: time, start: time, end: time) -> bool:
    if start <= end:
        return start <= now_t <= end
    return now_t >= start or now_t <= end


def _ensure_string_list(raw: Any) -> List[str]:
    if not isinstance(raw, Iterable) or isinstance(raw, (str, bytes, dict)):
        return []
    return [str(x).strip() for x in raw if str(x).strip()]


def _normalize_products(raw: Any) -> List[str]:
    return [item.upper() for item in _ensure_string_list(raw)]


def _is_itm_for_option_type(option_type: str, direction: str) -> bool:
    """
    对于 strike 方向判断 ITM/OTM:
    - call: lower=ITM, upper=OTM
    - put : lower=OTM, upper=ITM
    """
    option_type = (option_type or "").strip().lower()
    direction = (direction or "").strip().lower()
    if option_type == "call":
        return direction == "lower"
    if option_type == "put":
        return direction == "upper"
    return False


def _extract_expiry_from_symbol(vt_symbol: str) -> str:
    try:
        symbol = vt_symbol.split(".")[0] if "." in vt_symbol else vt_symbol
        m = re.search(r"([A-Za-z]+)(\d{4})", symbol)
        if m:
            return m.group(2)
    except Exception:
        return "unknown"
    return "unknown"
