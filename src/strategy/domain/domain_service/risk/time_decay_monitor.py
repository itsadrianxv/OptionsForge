"""
TimeDecayMonitor - 时间衰减监控服务

负责监控组合的时间衰减风险，识别临近到期的持仓，计算 Theta 指标。
"""

import logging
import re
from datetime import datetime
from typing import Dict, List

from ...entity.position import Position
from ...value_object.pricing.greeks import GreeksResult
from ...value_object.risk.risk import (
    TimeDecayConfig,
    ThetaMetrics,
    ExpiringPosition,
    ExpiryGroup,
)

logger = logging.getLogger(__name__)


class TimeDecayMonitor:
    """
    时间衰减监控服务
    
    职责:
    1. 计算组合总 Theta 和每日预期衰减金额
    2. 识别临近到期的持仓
    3. 按到期日分组统计持仓分布
    4. 生成到期提醒
    """
    
    def __init__(self, config: TimeDecayConfig) -> None:
        """
        初始化时间衰减监控器
        
        Args:
            config: 时间衰减监控配置对象
        """
        self._config = config
    
    def calculate_portfolio_theta(
        self,
        positions: List[Position],
        greeks_map: Dict[str, GreeksResult]
    ) -> ThetaMetrics:
        """
        计算组合 Theta 指标
        
        Args:
            positions: 活跃持仓列表
            greeks_map: 合约代码 -> Greeks 映射
            
        Returns:
            ThetaMetrics
        """
        total_theta = 0.0
        position_count = 0
        
        for pos in positions:
            if not pos.is_active or pos.volume <= 0:
                continue
            
            # 获取该持仓的 Greeks
            greeks = greeks_map.get(pos.vt_symbol)
            if greeks is None:
                logger.warning(f"Greeks not found for {pos.vt_symbol}, skipping")
                continue
            
            # 计算持仓的 Theta 贡献
            # Theta × volume × multiplier
            # 假设合约乘数为 10000（期权标准）
            multiplier = 10000.0
            position_theta = greeks.theta * pos.volume * multiplier
            
            total_theta += position_theta
            position_count += 1
        
        # 每日预期衰减金额 = |总 Theta|
        daily_decay_amount = abs(total_theta)
        
        return ThetaMetrics(
            total_theta=total_theta,
            daily_decay_amount=daily_decay_amount,
            position_count=position_count,
            timestamp=datetime.now()
        )
    
    def identify_expiring_positions(
        self,
        positions: List[Position],
        current_date: datetime
    ) -> List[ExpiringPosition]:
        """
        识别临近到期的持仓
        
        Args:
            positions: 活跃持仓列表
            current_date: 当前日期
            
        Returns:
            临近到期持仓列表
        """
        expiring_positions = []
        
        for pos in positions:
            if not pos.is_active or pos.volume <= 0:
                continue
            
            # 提取到期日
            expiry_date_str = self._extract_expiry_from_symbol(pos.vt_symbol)
            if expiry_date_str == "unknown":
                continue
            
            # 计算距离到期天数
            days_to_expiry = self._calculate_days_to_expiry(
                expiry_date_str, current_date
            )
            
            if days_to_expiry is None:
                continue
            
            # 判断是否需要提醒
            urgency = self._determine_urgency(days_to_expiry)
            if urgency is None:
                continue
            
            # 创建临近到期持仓记录
            expiring_pos = ExpiringPosition(
                vt_symbol=pos.vt_symbol,
                expiry_date=expiry_date_str,
                days_to_expiry=days_to_expiry,
                volume=pos.volume,
                theta=0.0,  # 可以后续从 greeks_map 获取
                urgency=urgency
            )
            expiring_positions.append(expiring_pos)
        
        return expiring_positions
    
    def calculate_expiry_distribution(
        self,
        positions: List[Position]
    ) -> Dict[str, ExpiryGroup]:
        """
        按到期日分组统计持仓分布
        
        Args:
            positions: 活跃持仓列表
            
        Returns:
            到期日 -> ExpiryGroup 映射
        """
        expiry_groups: Dict[str, ExpiryGroup] = {}
        
        for pos in positions:
            if not pos.is_active or pos.volume <= 0:
                continue
            
            # 提取到期日
            expiry_date_str = self._extract_expiry_from_symbol(pos.vt_symbol)
            
            # 如果该到期日还没有分组，创建新分组
            if expiry_date_str not in expiry_groups:
                expiry_groups[expiry_date_str] = ExpiryGroup(
                    expiry_date=expiry_date_str,
                    position_count=0,
                    total_volume=0,
                    total_theta=0.0,
                    positions=[]
                )
            
            # 更新分组统计
            group = expiry_groups[expiry_date_str]
            group.position_count += 1
            group.total_volume += pos.volume
            group.positions.append(pos.vt_symbol)
        
        return expiry_groups
    
    def _calculate_days_to_expiry(
        self,
        expiry_date_str: str,
        current_date: datetime
    ) -> int | None:
        """
        计算距离到期天数
        
        Args:
            expiry_date_str: 到期日字符串（如 "2401", "2509"）
            current_date: 当前日期
            
        Returns:
            距离到期天数，解析失败返回 None
        """
        try:
            # 解析到期日字符串（YYMM 格式）
            if len(expiry_date_str) == 4:
                year = int("20" + expiry_date_str[:2])
                month = int(expiry_date_str[2:])
                
                # 假设到期日是该月的第三个星期五（期权标准）
                # 简化处理：使用该月的 15 日作为近似
                expiry_date = datetime(year, month, 15)
                
                # 计算天数差
                days_diff = (expiry_date - current_date).days
                return days_diff
            else:
                logger.warning(f"Invalid expiry date format: {expiry_date_str}")
                return None
        except Exception as e:
            logger.warning(f"Error calculating days to expiry for {expiry_date_str}: {e}")
            return None
    
    def _determine_urgency(self, days_to_expiry: int) -> str | None:
        """
        判断到期紧急程度
        
        Args:
            days_to_expiry: 距离到期天数
            
        Returns:
            "warning" | "critical" | None（不需要提醒）
        """
        if days_to_expiry <= self._config.critical_expiry_days:
            return "critical"
        elif days_to_expiry <= self._config.expiry_warning_days:
            return "warning"
        else:
            return None
    
    def _extract_expiry_from_symbol(self, vt_symbol: str) -> str:
        """
        从合约代码中提取到期日
        
        期权合约格式示例: "IO2401-C-4000.CFFEX", "m2509-C-2800.DCE"
        提取年月部分作为到期日标识
        
        Args:
            vt_symbol: 合约代码
            
        Returns:
            到期日字符串（如 "2401", "2509"）
        """
        try:
            # 移除交易所后缀
            symbol = vt_symbol.split('.')[0]
            
            # 期权格式: 字母+年月+期权类型+行权价
            # 提取年月部分（通常是前面的数字部分）
            match = re.search(r'(\d{4})', symbol)
            if match:
                return match.group(1)
            
            logger.warning(f"Cannot extract expiry from {vt_symbol}")
            return "unknown"
        except Exception as e:
            logger.warning(f"Error extracting expiry from {vt_symbol}: {e}")
            return "unknown"
