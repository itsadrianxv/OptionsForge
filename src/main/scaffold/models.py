from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path


class CapabilityKey(str, Enum):
    """按需装配能力键。"""

    SELECTION = "selection"
    POSITION_SIZING = "position-sizing"
    PRICING = "pricing"
    GREEKS_RISK = "greeks-risk"
    EXECUTION = "execution"
    HEDGING = "hedging"
    MONITORING = "monitoring"
    OBSERVABILITY = "observability"


class CapabilityOptionKey(str, Enum):
    """能力组下的二级子选项。"""

    FUTURE_SELECTION = "future-selection"
    OPTION_CHAIN = "option-chain"
    OPTION_SELECTOR = "option-selector"
    POSITION_SIZING = "position-sizing"
    PRICING_ENGINE = "pricing-engine"
    GREEKS_CALCULATOR = "greeks-calculator"
    PORTFOLIO_RISK = "portfolio-risk"
    SMART_ORDER_EXECUTOR = "smart-order-executor"
    ADVANCED_ORDER_SCHEDULER = "advanced-order-scheduler"
    DELTA_HEDGING = "delta-hedging"
    VEGA_HEDGING = "vega-hedging"
    MONITORING = "monitoring"
    DECISION_OBSERVABILITY = "decision-observability"


class DirectoryConflictPolicy(str, Enum):
    """目标目录冲突策略。"""

    ABORT = "abort"
    CLEAR = "clear"
    OVERWRITE = "overwrite"


@dataclass(frozen=True)
class ConfigOverride:
    """创建时的配置参数覆盖。"""

    key: str
    value: object


@dataclass(frozen=True)
class CreateOptions:
    """`optionforge create` 输入参数。"""

    name: str | None
    destination: Path
    preset: str | None = None
    include_capabilities: tuple[CapabilityKey, ...] = ()
    exclude_capabilities: tuple[CapabilityKey, ...] = ()
    include_options: tuple[CapabilityOptionKey, ...] = ()
    exclude_options: tuple[CapabilityOptionKey, ...] = ()
    use_default: bool = False
    no_interactive: bool = False
    force: bool = False
    clear: bool = False
    overwrite: bool = False
    config_values: tuple[str, ...] = ()
    config_overrides: tuple[ConfigOverride, ...] = ()


@dataclass(frozen=True)
class ScaffoldPreset:
    """预设策略模板定义。"""

    key: str
    display_name: str
    description: str
    template_dir: Path | None
    default_options: tuple[CapabilityOptionKey, ...]
    indicator_class_template: str
    signal_class_template: str
    indicator_kwargs: dict[str, object]
    signal_kwargs: dict[str, object]


@dataclass(frozen=True)
class ScaffoldPlan:
    """渲染整个仓库脚手架所需的完整计划。"""

    project_name: str
    project_slug: str
    project_root: Path
    strategy_slug: str
    preset: ScaffoldPreset
    capabilities: tuple[CapabilityKey, ...]
    enabled_options: tuple[CapabilityOptionKey, ...]
    service_activation: dict[str, bool]
    conflict_policy: DirectoryConflictPolicy
    indicator_class_name: str
    signal_class_name: str
    base_copy_paths: tuple[str, ...]
    strategy_settings: dict[str, object]
    runtime_config: dict[str, object]
    observability_config: dict[str, object]
    position_sizing_config: dict[str, object]
    greeks_risk_config: dict[str, object]
    order_execution_config: dict[str, object]
    advanced_orders_config: dict[str, object]
    hedging_config: dict[str, object]
    indicator_kwargs: dict[str, object]
    signal_kwargs: dict[str, object]
    config_overrides: tuple[ConfigOverride, ...]

    @property
    def strategy_package_dir(self) -> Path:
        return self.project_root / "src" / "strategies" / self.strategy_slug

    @property
    def indicator_import_path(self) -> str:
        return f"src.strategies.{self.strategy_slug}.indicator_service:{self.indicator_class_name}"

    @property
    def signal_import_path(self) -> str:
        return f"src.strategies.{self.strategy_slug}.signal_service:{self.signal_class_name}"


@dataclass(frozen=True)
class AutoFixPreview:
    """交互模式下的自动修复预览。"""

    error: str
    suggestion: str
    add_options: tuple[CapabilityOptionKey, ...] = ()
    remove_options: tuple[CapabilityOptionKey, ...] = ()
