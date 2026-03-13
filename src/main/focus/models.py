from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from src.cli.common import CliEntryMetadata


@dataclass(frozen=True)
class StrategyMetadata:
    name: str
    trading_target: str
    strategy_type: str
    run_mode: str
    summary: str


@dataclass(frozen=True)
class AcceptanceSpec:
    summary: str
    completion_checks: tuple[str, ...]
    minimal_test_command: str
    test_selectors: tuple[str, ...]
    key_logs: tuple[str, ...]
    key_outputs: tuple[str, ...]


@dataclass(frozen=True)
class FocusManifest:
    manifest_path: Path
    strategy: StrategyMetadata
    packs: tuple[str, ...]
    cli: CliEntryMetadata
    entrypoints: dict[str, str]
    editable_paths: tuple[str, ...]
    reference_paths: tuple[str, ...]
    frozen_paths: tuple[str, ...]
    acceptance: AcceptanceSpec


@dataclass(frozen=True)
class PackDefinition:
    key: str
    manifest_path: Path
    depends_on: tuple[str, ...]
    owned_paths: tuple[str, ...]
    config_keys: tuple[str, ...]
    test_selectors: tuple[str, ...]
    cli_commands: tuple[str, ...]
    shell_commands: tuple[str, ...]
    commands: tuple[str, ...]
    agent_notes: tuple[str, ...]


@dataclass(frozen=True)
class SkippedPackTests:
    pack_key: str
    missing_modules: tuple[str, ...]


@dataclass(frozen=True)
class FocusTestMatrix:
    smoke_selectors: tuple[str, ...]
    full_selectors: tuple[str, ...]
    skipped_packs: tuple[SkippedPackTests, ...]
    smoke_keyword_expression: str
    smoke_filter_descriptions: tuple[str, ...]


@dataclass(frozen=True)
class FocusPointer:
    strategy: str
    manifest_path: Path


@dataclass(frozen=True)
class FocusContext:
    repo_root: Path
    pointer: FocusPointer
    manifest: FocusManifest
    resolved_packs: tuple[PackDefinition, ...]

    @property
    def nav_dir(self) -> Path:
        return self.repo_root / ".focus"

    @property
    def system_map_path(self) -> Path:
        return self.nav_dir / "SYSTEM_MAP.md"

    @property
    def active_surface_path(self) -> Path:
        return self.nav_dir / "ACTIVE_SURFACE.md"

    @property
    def task_brief_path(self) -> Path:
        return self.nav_dir / "TASK_BRIEF.md"

    @property
    def commands_path(self) -> Path:
        return self.nav_dir / "COMMANDS.md"

    @property
    def task_router_path(self) -> Path:
        return self.nav_dir / "TASK_ROUTER.md"

    @property
    def test_matrix_path(self) -> Path:
        return self.nav_dir / "TEST_MATRIX.md"

    @property
    def context_json_path(self) -> Path:
        return self.nav_dir / "context.json"
