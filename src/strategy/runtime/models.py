from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable


RuntimeCallable = Callable[..., Any]


@dataclass(slots=True)
class RuntimeKernel:
    entry: Any
    logger: Any | None = None


@dataclass(slots=True)
class LifecycleRoles:
    init_hooks: tuple[RuntimeCallable, ...] = ()
    cleanup_hooks: tuple[RuntimeCallable, ...] = ()


@dataclass(slots=True)
class UniverseRoles:
    initializer: RuntimeCallable | None = None
    rollover_checker: RuntimeCallable | None = None


@dataclass(slots=True)
class OpenPipelineRoles:
    option_chain_loader: RuntimeCallable | None = None
    contract_selector: RuntimeCallable | None = None
    greeks_enricher: RuntimeCallable | None = None
    pricing_enricher: RuntimeCallable | None = None
    risk_evaluator: RuntimeCallable | None = None
    sizing_evaluator: RuntimeCallable | None = None
    execution_planner: RuntimeCallable | None = None
    execution_scheduler: RuntimeCallable | None = None


@dataclass(slots=True)
class ClosePipelineRoles:
    risk_evaluator: RuntimeCallable | None = None
    exit_intent_provider: RuntimeCallable | None = None
    exposure_group_resolver: RuntimeCallable | None = None
    freshness_guard: RuntimeCallable | None = None
    close_volume_planner: RuntimeCallable | None = None
    execution_planner: RuntimeCallable | None = None
    execution_scheduler: RuntimeCallable | None = None


@dataclass(slots=True)
class PortfolioRoles:
    rebalance_planner: RuntimeCallable | None = None


@dataclass(slots=True)
class StateRoles:
    snapshot_sinks: tuple[RuntimeCallable, ...] = ()
    snapshot_dumpers: tuple[RuntimeCallable, ...] = ()
    restore_hooks: tuple[RuntimeCallable, ...] = ()


@dataclass(slots=True)
class ObservabilityRoles:
    trace_sinks: tuple[RuntimeCallable, ...] = ()


@dataclass(slots=True)
class CapabilityContribution:
    lifecycle: LifecycleRoles = field(default_factory=LifecycleRoles)
    universe: UniverseRoles = field(default_factory=UniverseRoles)
    open_pipeline: OpenPipelineRoles = field(default_factory=OpenPipelineRoles)
    close_pipeline: ClosePipelineRoles = field(default_factory=ClosePipelineRoles)
    portfolio: PortfolioRoles = field(default_factory=PortfolioRoles)
    state: StateRoles = field(default_factory=StateRoles)
    observability: ObservabilityRoles = field(default_factory=ObservabilityRoles)


@dataclass(slots=True)
class StrategyRuntime:
    enabled_capabilities: tuple[str, ...]
    kernel: RuntimeKernel
    lifecycle: LifecycleRoles = field(default_factory=LifecycleRoles)
    universe: UniverseRoles = field(default_factory=UniverseRoles)
    open_pipeline: OpenPipelineRoles = field(default_factory=OpenPipelineRoles)
    close_pipeline: ClosePipelineRoles = field(default_factory=ClosePipelineRoles)
    portfolio: PortfolioRoles = field(default_factory=PortfolioRoles)
    state: StateRoles = field(default_factory=StateRoles)
    observability: ObservabilityRoles = field(default_factory=ObservabilityRoles)
