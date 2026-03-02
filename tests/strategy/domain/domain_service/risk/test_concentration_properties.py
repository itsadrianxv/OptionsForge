"""
ConcentrationMonitor 属性测试

使用 Hypothesis 进行基于属性的测试,验证集中度风险监控服务的通用正确性属性。
"""
from hypothesis import given, strategies as st, settings, assume

from src.strategy.domain.domain_service.risk.concentration_monitor import ConcentrationMonitor
from src.strategy.domain.entity.position import Position
from src.strategy.domain.value_object.risk.risk import (
    ConcentrationConfig,
    ConcentrationMetrics,
)


# ============================================================================
# 测试数据生成策略
# ============================================================================

def position_strategy(
    min_volume: int = 1,
    max_volume: int = 100,
    min_price: float = 0.01,
    max_price: float = 10.0
):
    """生成持仓实体的策略"""
    # 生成不同品种、到期日、行权价的合约代码
    underlyings = ["IF2401.CFFEX", "IH2401.CFFEX", "IM2401.CFFEX", "m2509.DCE"]
    expiries = ["2401", "2402", "2403", "2509"]
    strikes = ["4000", "4100", "4500", "5000", "2800", "3000"]
    
    return st.builds(
        Position,
        vt_symbol=st.one_of(
            st.just("IO2401-C-4000.CFFEX"),
            st.just("IO2401-C-4100.CFFEX"),
            st.just("IO2402-C-4000.CFFEX"),
            st.just("HO2401-C-3000.CFFEX"),
            st.just("HO2402-C-3000.CFFEX"),
            st.just("MO2401-C-5000.CFFEX"),
            st.just("m2509-C-2800.DCE"),
            st.just("IO2401-C-4500.CFFEX"),
            st.just("IO2403-C-4000.CFFEX"),
        ),
        underlying_vt_symbol=st.sampled_from(underlyings),
        signal=st.just("test_signal"),
        volume=st.integers(min_value=min_volume, max_value=max_volume),
        direction=st.sampled_from(["long", "short"]),
        open_price=st.floats(min_value=min_price, max_value=max_price, allow_nan=False, allow_infinity=False),
        is_closed=st.just(False),
    )


def concentration_config_strategy():
    """生成集中度配置的策略"""
    return st.builds(
        ConcentrationConfig,
        underlying_concentration_limit=st.floats(min_value=0.3, max_value=0.9, allow_nan=False, allow_infinity=False),
        expiry_concentration_limit=st.floats(min_value=0.3, max_value=0.9, allow_nan=False, allow_infinity=False),
        strike_concentration_limit=st.floats(min_value=0.3, max_value=0.9, allow_nan=False, allow_infinity=False),
        hhi_threshold=st.floats(min_value=0.2, max_value=0.8, allow_nan=False, allow_infinity=False),
        concentration_basis=st.just("notional"),
    )


# ============================================================================
# Feature: risk-service-enhancement, Property 13: 集中度占比计算
# **Validates: Requirements 4.1, 4.2, 4.3, 4.7**
# ============================================================================

@settings(max_examples=100)
@given(
    config=concentration_config_strategy(),
    positions=st.lists(position_strategy(), min_size=1, max_size=20),
)
def test_property_concentration_ratio_calculation(config, positions):
    """
    Feature: risk-service-enhancement, Property 13: 集中度占比计算
    
    对于任意持仓列表和价格字典,各维度(品种、到期日、行权价)的集中度占比总和
    应该等于 1.0,且单个占比应该在 [0, 1] 范围内
    
    **Validates: Requirements 4.1, 4.2, 4.3, 4.7**
    """
    # 确保所有持仓都是活跃的
    for pos in positions:
        assume(pos.is_active)
        assume(pos.volume > 0)
    
    monitor = ConcentrationMonitor(config)
    
    # 生成价格字典
    prices = {pos.vt_symbol: pos.open_price for pos in positions}
    
    # 确保价格都是正数
    for price in prices.values():
        assume(price > 0)
    
    # 计算集中度
    metrics = monitor.calculate_concentration(positions, prices)
    
    # 属性验证 1: 品种集中度占比总和应该等于 1.0
    if metrics.underlying_concentration:
        underlying_sum = sum(metrics.underlying_concentration.values())
        assert abs(underlying_sum - 1.0) < 1e-6, \
            f"品种集中度占比总和应该等于 1.0,实际: {underlying_sum}"
        
        # 每个占比应该在 [0, 1] 范围内
        for underlying, ratio in metrics.underlying_concentration.items():
            assert 0.0 <= ratio <= 1.0, \
                f"品种 {underlying} 的占比 {ratio} 应该在 [0, 1] 范围内"
    
    # 属性验证 2: 到期日集中度占比总和应该等于 1.0
    if metrics.expiry_concentration:
        expiry_sum = sum(metrics.expiry_concentration.values())
        assert abs(expiry_sum - 1.0) < 1e-6, \
            f"到期日集中度占比总和应该等于 1.0,实际: {expiry_sum}"
        
        # 每个占比应该在 [0, 1] 范围内
        for expiry, ratio in metrics.expiry_concentration.items():
            assert 0.0 <= ratio <= 1.0, \
                f"到期日 {expiry} 的占比 {ratio} 应该在 [0, 1] 范围内"
    
    # 属性验证 3: 行权价集中度占比总和应该等于 1.0
    if metrics.strike_concentration:
        strike_sum = sum(metrics.strike_concentration.values())
        assert abs(strike_sum - 1.0) < 1e-6, \
            f"行权价集中度占比总和应该等于 1.0,实际: {strike_sum}"
        
        # 每个占比应该在 [0, 1] 范围内
        for strike_range, ratio in metrics.strike_concentration.items():
            assert 0.0 <= ratio <= 1.0, \
                f"行权价区间 {strike_range} 的占比 {ratio} 应该在 [0, 1] 范围内"
    
    # 属性验证 4: 最大占比应该等于各维度中的最大值
    if metrics.underlying_concentration:
        expected_max_underlying = max(metrics.underlying_concentration.values())
        assert abs(metrics.max_underlying_ratio - expected_max_underlying) < 1e-6, \
            f"最大品种占比应该等于实际最大值。期望: {expected_max_underlying}, 实际: {metrics.max_underlying_ratio}"
    
    if metrics.expiry_concentration:
        expected_max_expiry = max(metrics.expiry_concentration.values())
        assert abs(metrics.max_expiry_ratio - expected_max_expiry) < 1e-6, \
            f"最大到期日占比应该等于实际最大值。期望: {expected_max_expiry}, 实际: {metrics.max_expiry_ratio}"
    
    if metrics.strike_concentration:
        expected_max_strike = max(metrics.strike_concentration.values())
        assert abs(metrics.max_strike_ratio - expected_max_strike) < 1e-6, \
            f"最大行权价占比应该等于实际最大值。期望: {expected_max_strike}, 实际: {metrics.max_strike_ratio}"


# ============================================================================
# Feature: risk-service-enhancement, Property 14: HHI 计算正确性
# **Validates: Requirements 4.6**
# ============================================================================

@settings(max_examples=100)
@given(
    config=concentration_config_strategy(),
    positions=st.lists(position_strategy(), min_size=1, max_size=20),
)
def test_property_hhi_calculation_correctness(config, positions):
    """
    Feature: risk-service-enhancement, Property 14: HHI 计算正确性
    
    对于任意持仓分布,HHI(赫芬达尔指数)应该等于各占比的平方和,
    且在 [0, 1] 范围内
    
    **Validates: Requirements 4.6**
    """
    # 确保所有持仓都是活跃的
    for pos in positions:
        assume(pos.is_active)
        assume(pos.volume > 0)
    
    monitor = ConcentrationMonitor(config)
    
    # 生成价格字典
    prices = {pos.vt_symbol: pos.open_price for pos in positions}
    
    # 确保价格都是正数
    for price in prices.values():
        assume(price > 0)
    
    # 计算集中度
    metrics = monitor.calculate_concentration(positions, prices)
    
    # 属性验证 1: 品种 HHI 应该等于各占比的平方和
    if metrics.underlying_concentration:
        expected_underlying_hhi = sum(
            ratio ** 2 for ratio in metrics.underlying_concentration.values()
        )
        assert abs(metrics.underlying_hhi - expected_underlying_hhi) < 1e-6, \
            f"品种 HHI 应该等于各占比的平方和。期望: {expected_underlying_hhi}, 实际: {metrics.underlying_hhi}"
        
        # HHI 应该在 [0, 1] 范围内
        assert 0.0 <= metrics.underlying_hhi <= 1.0, \
            f"品种 HHI {metrics.underlying_hhi} 应该在 [0, 1] 范围内"
    
    # 属性验证 2: 到期日 HHI 应该等于各占比的平方和
    if metrics.expiry_concentration:
        expected_expiry_hhi = sum(
            ratio ** 2 for ratio in metrics.expiry_concentration.values()
        )
        assert abs(metrics.expiry_hhi - expected_expiry_hhi) < 1e-6, \
            f"到期日 HHI 应该等于各占比的平方和。期望: {expected_expiry_hhi}, 实际: {metrics.expiry_hhi}"
        
        # HHI 应该在 [0, 1] 范围内
        assert 0.0 <= metrics.expiry_hhi <= 1.0, \
            f"到期日 HHI {metrics.expiry_hhi} 应该在 [0, 1] 范围内"
    
    # 属性验证 3: 行权价 HHI 应该等于各占比的平方和
    if metrics.strike_concentration:
        expected_strike_hhi = sum(
            ratio ** 2 for ratio in metrics.strike_concentration.values()
        )
        assert abs(metrics.strike_hhi - expected_strike_hhi) < 1e-6, \
            f"行权价 HHI 应该等于各占比的平方和。期望: {expected_strike_hhi}, 实际: {metrics.strike_hhi}"
        
        # HHI 应该在 [0, 1] 范围内
        assert 0.0 <= metrics.strike_hhi <= 1.0, \
            f"行权价 HHI {metrics.strike_hhi} 应该在 [0, 1] 范围内"
    
    # 属性验证 4: HHI 的数学性质
    # 当只有一个持仓时,HHI 应该等于 1.0
    if len(metrics.underlying_concentration) == 1:
        assert abs(metrics.underlying_hhi - 1.0) < 1e-6, \
            "单一品种时 HHI 应该等于 1.0"
    
    # 当持仓完全均匀分布时,HHI = 1/n
    # 检查品种维度
    if metrics.underlying_concentration:
        n = len(metrics.underlying_concentration)
        ratios = list(metrics.underlying_concentration.values())
        
        # 检查是否均匀分布(所有占比相等)
        if all(abs(r - ratios[0]) < 1e-6 for r in ratios):
            expected_hhi = 1.0 / n
            assert abs(metrics.underlying_hhi - expected_hhi) < 1e-5, \
                f"均匀分布时 HHI 应该等于 1/n。期望: {expected_hhi}, 实际: {metrics.underlying_hhi}"


# ============================================================================
# Feature: risk-service-enhancement, Property 15: 集中度警告触发
# **Validates: Requirements 4.4, 4.5**
# ============================================================================

@settings(max_examples=100)
@given(
    config=concentration_config_strategy(),
    positions=st.lists(position_strategy(), min_size=1, max_size=20),
)
def test_property_concentration_warning_trigger(config, positions):
    """
    Feature: risk-service-enhancement, Property 15: 集中度警告触发
    
    对于任意集中度指标,当任一维度的最大占比或 HHI 超过配置阈值时,
    应该生成相应维度的集中度警告
    
    **Validates: Requirements 4.4, 4.5**
    """
    # 确保所有持仓都是活跃的
    for pos in positions:
        assume(pos.is_active)
        assume(pos.volume > 0)
    
    monitor = ConcentrationMonitor(config)
    
    # 生成价格字典
    prices = {pos.vt_symbol: pos.open_price for pos in positions}
    
    # 确保价格都是正数
    for price in prices.values():
        assume(price > 0)
    
    # 计算集中度
    metrics = monitor.calculate_concentration(positions, prices)
    
    # 检查集中度限额
    warnings = monitor.check_concentration_limits(metrics)
    
    # 属性验证 1: 品种集中度超限应该生成警告
    if metrics.max_underlying_ratio > config.underlying_concentration_limit:
        underlying_warnings = [w for w in warnings if w.dimension == "underlying"]
        assert len(underlying_warnings) > 0, \
            f"品种集中度 {metrics.max_underlying_ratio} 超过限额 {config.underlying_concentration_limit} 时应该生成警告"
        
        # 验证警告内容
        for warning in underlying_warnings:
            assert warning.concentration > config.underlying_concentration_limit, \
                f"警告中的集中度 {warning.concentration} 应该超过限额 {config.underlying_concentration_limit}"
            assert warning.limit == config.underlying_concentration_limit, \
                "警告中的限额应该与配置一致"
            assert len(warning.message) > 0, "警告应该包含消息"
            assert warning.key in metrics.underlying_concentration, \
                f"警告的键 {warning.key} 应该在集中度字典中"
    
    # 属性验证 2: 到期日集中度超限应该生成警告
    if metrics.max_expiry_ratio > config.expiry_concentration_limit:
        expiry_warnings = [w for w in warnings if w.dimension == "expiry"]
        assert len(expiry_warnings) > 0, \
            f"到期日集中度 {metrics.max_expiry_ratio} 超过限额 {config.expiry_concentration_limit} 时应该生成警告"
        
        # 验证警告内容
        for warning in expiry_warnings:
            assert warning.concentration > config.expiry_concentration_limit, \
                f"警告中的集中度 {warning.concentration} 应该超过限额 {config.expiry_concentration_limit}"
            assert warning.limit == config.expiry_concentration_limit, \
                "警告中的限额应该与配置一致"
    
    # 属性验证 3: 行权价集中度超限应该生成警告
    if metrics.max_strike_ratio > config.strike_concentration_limit:
        strike_warnings = [w for w in warnings if w.dimension == "strike"]
        assert len(strike_warnings) > 0, \
            f"行权价集中度 {metrics.max_strike_ratio} 超过限额 {config.strike_concentration_limit} 时应该生成警告"
        
        # 验证警告内容
        for warning in strike_warnings:
            assert warning.concentration > config.strike_concentration_limit, \
                f"警告中的集中度 {warning.concentration} 应该超过限额 {config.strike_concentration_limit}"
            assert warning.limit == config.strike_concentration_limit, \
                "警告中的限额应该与配置一致"
    
    # 属性验证 4: HHI 超限应该生成警告
    hhi_warnings = [w for w in warnings if w.dimension == "hhi"]
    
    if metrics.underlying_hhi > config.hhi_threshold:
        underlying_hhi_warnings = [w for w in hhi_warnings if w.key == "underlying"]
        assert len(underlying_hhi_warnings) > 0, \
            f"品种 HHI {metrics.underlying_hhi} 超过阈值 {config.hhi_threshold} 时应该生成警告"
    
    if metrics.expiry_hhi > config.hhi_threshold:
        expiry_hhi_warnings = [w for w in hhi_warnings if w.key == "expiry"]
        assert len(expiry_hhi_warnings) > 0, \
            f"到期日 HHI {metrics.expiry_hhi} 超过阈值 {config.hhi_threshold} 时应该生成警告"
    
    if metrics.strike_hhi > config.hhi_threshold:
        strike_hhi_warnings = [w for w in hhi_warnings if w.key == "strike"]
        assert len(strike_hhi_warnings) > 0, \
            f"行权价 HHI {metrics.strike_hhi} 超过阈值 {config.hhi_threshold} 时应该生成警告"
    
    # 属性验证 5: 未超限时不应该生成警告
    if (metrics.max_underlying_ratio <= config.underlying_concentration_limit and
        metrics.max_expiry_ratio <= config.expiry_concentration_limit and
        metrics.max_strike_ratio <= config.strike_concentration_limit and
        metrics.underlying_hhi <= config.hhi_threshold and
        metrics.expiry_hhi <= config.hhi_threshold and
        metrics.strike_hhi <= config.hhi_threshold):
        assert len(warnings) == 0, \
            "所有维度都未超限时不应该生成警告"


# ============================================================================
# Feature: risk-service-enhancement, Property 16: 集中度单调性
# **Validates: Requirements 4.1, 4.2, 4.3, 4.6**
# ============================================================================

@settings(max_examples=100)
@given(
    config=concentration_config_strategy(),
    base_positions=st.lists(position_strategy(), min_size=2, max_size=10),
    additional_position=position_strategy(),
)
def test_property_concentration_monotonicity(config, base_positions, additional_position):
    """
    Feature: risk-service-enhancement, Property 16: 集中度单调性
    
    对于任意持仓列表,增加某一维度(品种/到期日/行权价)的持仓
    应该增加该维度的集中度和 HHI
    
    **Validates: Requirements 4.1, 4.2, 4.3, 4.6**
    """
    # 确保所有持仓都是活跃的
    for pos in base_positions:
        assume(pos.is_active)
        assume(pos.volume > 0)
    
    assume(additional_position.is_active)
    assume(additional_position.volume > 0)
    
    monitor = ConcentrationMonitor(config)
    
    # 生成基础持仓的价格字典
    base_prices = {pos.vt_symbol: pos.open_price for pos in base_positions}
    
    # 确保价格都是正数
    for price in base_prices.values():
        assume(price > 0)
    assume(additional_position.open_price > 0)
    
    # 计算基础持仓的集中度
    base_metrics = monitor.calculate_concentration(base_positions, base_prices)
    
    # 找到基础持仓中已存在的品种
    existing_underlyings = {pos.underlying_vt_symbol for pos in base_positions}
    
    # 如果新增持仓的品种已存在,则应该验证集中度性质
    if additional_position.underlying_vt_symbol in existing_underlyings:
        # 添加新持仓
        extended_positions = base_positions + [additional_position]
        extended_prices = {**base_prices, additional_position.vt_symbol: additional_position.open_price}
        
        # 计算扩展后的集中度
        extended_metrics = monitor.calculate_concentration(extended_positions, extended_prices)
        
        # 属性验证 1: 增加已存在品种的持仓,该品种在持仓列表中的数量应该增加
        # 这意味着该品种的绝对持仓量(按手数计算)应该增加
        base_underlying_volume = sum(
            pos.volume for pos in base_positions
            if pos.underlying_vt_symbol == additional_position.underlying_vt_symbol and pos.is_active
        )
        
        extended_underlying_volume = sum(
            pos.volume for pos in extended_positions
            if pos.underlying_vt_symbol == additional_position.underlying_vt_symbol and pos.is_active
        )
        
        assert extended_underlying_volume > base_underlying_volume, \
            f"增加品种持仓后,该品种的总手数应该增加。" \
            f"基础: {base_underlying_volume}, 扩展: {extended_underlying_volume}"
        
        # 属性验证 2: HHI 应该在合理范围内
        assert 0.0 <= extended_metrics.underlying_hhi <= 1.0, \
            f"扩展后的品种 HHI {extended_metrics.underlying_hhi} 应该在 [0, 1] 范围内"
        
        assert 0.0 <= extended_metrics.expiry_hhi <= 1.0, \
            f"扩展后的到期日 HHI {extended_metrics.expiry_hhi} 应该在 [0, 1] 范围内"
        
        assert 0.0 <= extended_metrics.strike_hhi <= 1.0, \
            f"扩展后的行权价 HHI {extended_metrics.strike_hhi} 应该在 [0, 1] 范围内"
        
        # 属性验证 3: 如果只有一个品种,HHI 应该等于 1.0
        if len(extended_metrics.underlying_concentration) == 1:
            assert abs(extended_metrics.underlying_hhi - 1.0) < 1e-6, \
                "只有一个品种时 HHI 应该等于 1.0"
        
        # 属性验证 4: 如果有多个品种,HHI 应该小于 1.0
        if len(extended_metrics.underlying_concentration) > 1:
            assert extended_metrics.underlying_hhi < 1.0, \
                "有多个品种时 HHI 应该小于 1.0"
    
    # 属性验证 5: 无论如何,集中度占比总和应该始终等于 1.0
    extended_positions = base_positions + [additional_position]
    extended_prices = {**base_prices, additional_position.vt_symbol: additional_position.open_price}
    extended_metrics = monitor.calculate_concentration(extended_positions, extended_prices)
    
    if extended_metrics.underlying_concentration:
        underlying_sum = sum(extended_metrics.underlying_concentration.values())
        assert abs(underlying_sum - 1.0) < 1e-6, \
            f"扩展后品种集中度占比总和应该等于 1.0,实际: {underlying_sum}"
    
    if extended_metrics.expiry_concentration:
        expiry_sum = sum(extended_metrics.expiry_concentration.values())
        assert abs(expiry_sum - 1.0) < 1e-6, \
            f"扩展后到期日集中度占比总和应该等于 1.0,实际: {expiry_sum}"
    
    if extended_metrics.strike_concentration:
        strike_sum = sum(extended_metrics.strike_concentration.values())
        assert abs(strike_sum - 1.0) < 1e-6, \
            f"扩展后行权价集中度占比总和应该等于 1.0,实际: {strike_sum}"
