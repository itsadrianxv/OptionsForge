from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from src.main.scaffold.models import CapabilityKey, CapabilityOptionKey, ConfigOverride


@dataclass(frozen=True)
class SpecStrategy:
    name: str
    summary: str
    trading_target: str
    strategy_type: str
    run_mode: str


@dataclass(frozen=True)
class SpecScaffold:
    preset: str
    capabilities: tuple[CapabilityKey, ...]
    options: tuple[CapabilityOptionKey, ...]


@dataclass(frozen=True)
class SpecLogic:
    entry_rules: tuple[str, ...]
    exit_rules: tuple[str, ...]
    selection_rules: tuple[str, ...]
    sizing_rules: tuple[str, ...]
    risk_rules: tuple[str, ...]
    hedging_rules: tuple[str, ...]
    observability_notes: tuple[str, ...]


@dataclass(frozen=True)
class SpecAcceptance:
    completion_checks: tuple[str, ...]
    focus_packs: tuple[str, ...]
    test_scenarios: tuple[str, ...]


@dataclass(frozen=True)
class StrategySpec:
    spec_path: Path
    strategy: SpecStrategy
    scaffold: SpecScaffold
    config_overrides: tuple[ConfigOverride, ...]
    logic: SpecLogic
    acceptance: SpecAcceptance
