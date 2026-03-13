from __future__ import annotations

from collections.abc import Iterable
import importlib
import json
from pathlib import Path
import re
import tomllib

from src.cli.common import (
    CliEntryMetadata,
    cli_entry_metadata_payload,
    get_cli_entry_metadata,
    render_cli_command,
    render_cli_commands,
)
from .models import (
    AcceptanceSpec,
    FocusContext,
    FocusManifest,
    FocusPointer,
    FocusTestMatrix,
    PackDefinition,
    SkippedPackTests,
    StrategyMetadata,
)
from .renderer import (
    build_recommended_first_pass,
    render_active_surface,
    render_commands,
    render_system_map,
    render_task_brief,
    render_task_router,
    render_test_matrix,
)

FOCUS_ROOT = Path("focus")
PACKS_ROOT = FOCUS_ROOT / "packs"
STRATEGIES_ROOT = FOCUS_ROOT / "strategies"
STATE_ROOT = Path(".focus")
MANIFEST_FILENAME = "strategy.manifest.toml"
CURRENT_POINTER_FILENAME = "current.toml"
REQUIRED_ENTRYPOINT_KEYS: tuple[str, ...] = ("run", "backtest", "validate", "monitor")
DEFAULT_PACK_KEYS: tuple[str, ...] = (
    "kernel",
    "selection",
    "pricing",
    "risk",
    "execution",
    "hedging",
    "monitoring",
    "web",
    "deploy",
    "backtest",
)
DEFAULT_EDITABLE_PATHS: tuple[str, ...] = (
    "src/strategy/strategy_entry.py",
    "src/strategy/application",
    "src/strategy/domain",
    "config/strategy_config.toml",
    "config/general/trading_target.toml",
    "config/domain_service",
    "tests/strategy",
    "tests/web",
)
DEFAULT_REFERENCE_PATHS: tuple[str, ...] = (
    "src/main",
    "src/backtesting",
    "src/web",
    "src/cli",
    "src/main/scaffold",
    "tests/backtesting",
    "tests/main/scaffold",
    "deploy",
    "doc",
    "README.md",
)
DEFAULT_FROZEN_PATHS: tuple[str, ...] = (
    ".codex",
    ".git",
    ".venv",
    ".pytest_cache",
    ".hypothesis",
    "temp",
    "LICENSE",
)
PACK_REQUIRED_MODULES: dict[str, tuple[str, ...]] = {
    "backtest": ("chinese_calendar",),
}
SMOKE_TEST_EXCLUDE_KEYWORDS: tuple[str, ...] = ("property", "pbt")
WIDE_FOCUS_PACK_THRESHOLD = 6
WIDE_FOCUS_EDITABLE_THRESHOLD = 6


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9_]+", "_", value.strip())
    slug = re.sub(r"_+", "_", slug).strip("_")
    return slug.lower() or "main"


def manifest_path_for(repo_root: Path, strategy_name: str) -> Path:
    return repo_root / STRATEGIES_ROOT / slugify(strategy_name) / MANIFEST_FILENAME


def current_pointer_path_for(repo_root: Path) -> Path:
    return repo_root / STATE_ROOT / CURRENT_POINTER_FILENAME


def _generated_doc_paths(repo_root: Path) -> tuple[Path, Path, Path, Path, Path, Path]:
    nav_dir = repo_root / STATE_ROOT
    return (
        nav_dir / "SYSTEM_MAP.md",
        nav_dir / "ACTIVE_SURFACE.md",
        nav_dir / "TASK_BRIEF.md",
        nav_dir / "COMMANDS.md",
        nav_dir / "TASK_ROUTER.md",
        nav_dir / "TEST_MATRIX.md",
    )


def context_json_path_for(repo_root: Path) -> Path:
    return repo_root / STATE_ROOT / "context.json"


def _read_toml(path: Path) -> dict[str, object]:
    return tomllib.loads(path.read_text(encoding="utf-8"))


def _ensure_string(value: object, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"`{field_name}` 必须是非空字符串。")
    return value.strip()


def _ensure_string_tuple(value: object, field_name: str) -> tuple[str, ...]:
    if not isinstance(value, list):
        raise ValueError(f"`{field_name}` 必须是字符串数组。")
    items: list[str] = []
    for item in value:
        if not isinstance(item, str) or not item.strip():
            raise ValueError(f"`{field_name}` 中存在空字符串。")
        items.append(item.strip())
    return tuple(items)


def _quote(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def _selector_base_path(selector: str) -> str:
    return selector.split("::", 1)[0].strip()


def _validate_repo_path(repo_root: Path, relative_path: str, field_name: str) -> None:
    path = repo_root / relative_path
    if not path.exists():
        raise ValueError(f"`{field_name}` 引用了不存在的路径: {relative_path}")


def _validate_selector(repo_root: Path, selector: str, field_name: str) -> None:
    base_path = _selector_base_path(selector)
    if not base_path:
        raise ValueError(f"`{field_name}` 中存在空 selector。")
    if base_path.startswith("-"):
        return
    _validate_repo_path(repo_root, base_path, field_name)


def _render_pack_commands(
    cli_commands: tuple[str, ...],
    shell_commands: tuple[str, ...],
    *,
    cli_metadata: CliEntryMetadata | None = None,
) -> tuple[str, ...]:
    rendered_cli_commands = render_cli_commands(cli_commands, metadata=cli_metadata or get_cli_entry_metadata())
    return (*rendered_cli_commands, *shell_commands)


def load_pack_catalog(repo_root: Path) -> dict[str, PackDefinition]:
    pack_root = repo_root / PACKS_ROOT
    if not pack_root.exists():
        raise ValueError(f"未找到 pack 元数据目录: {PACKS_ROOT.as_posix()}")

    cli_metadata = get_cli_entry_metadata()
    catalog: dict[str, PackDefinition] = {}
    for pack_key in DEFAULT_PACK_KEYS:
        pack_path = pack_root / pack_key / "pack.toml"
        if not pack_path.exists():
            raise ValueError(f"缺少 pack 元数据文件: {(PACKS_ROOT / pack_key / 'pack.toml').as_posix()}")
        raw = _read_toml(pack_path)
        key = _ensure_string(raw.get("key"), f"{pack_path.name}.key")
        cli_commands = _ensure_string_tuple(raw.get("cli_commands", []), f"{key}.cli_commands")
        shell_commands = _ensure_string_tuple(raw.get("shell_commands", []), f"{key}.shell_commands")
        definition = PackDefinition(
            key=key,
            manifest_path=pack_path,
            depends_on=_ensure_string_tuple(raw.get("depends_on", []), f"{key}.depends_on"),
            owned_paths=_ensure_string_tuple(raw.get("owned_paths", []), f"{key}.owned_paths"),
            config_keys=_ensure_string_tuple(raw.get("config_keys", []), f"{key}.config_keys"),
            test_selectors=_ensure_string_tuple(raw.get("test_selectors", []), f"{key}.test_selectors"),
            cli_commands=cli_commands,
            shell_commands=shell_commands,
            commands=_render_pack_commands(cli_commands, shell_commands, cli_metadata=cli_metadata),
            agent_notes=_ensure_string_tuple(raw.get("agent_notes", []), f"{key}.agent_notes"),
        )
        catalog[key] = definition

    for key, definition in catalog.items():
        for dependency in definition.depends_on:
            if dependency not in catalog:
                raise ValueError(f"pack `{key}` 依赖了未知 pack `{dependency}`。")
        for owned_path in definition.owned_paths:
            _validate_repo_path(repo_root, owned_path, f"{key}.owned_paths")
        for selector in definition.test_selectors:
            _validate_selector(repo_root, selector, f"{key}.test_selectors")

    _resolve_pack_keys(tuple(catalog.keys()), catalog)
    return catalog


def _resolve_pack_keys(pack_keys: tuple[str, ...], catalog: dict[str, PackDefinition]) -> tuple[str, ...]:
    resolved: list[str] = []
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(key: str, trail: tuple[str, ...]) -> None:
        if key not in catalog:
            raise ValueError(f"未知 pack: {key}")
        if key in visited:
            return
        if key in visiting:
            chain = " -> ".join((*trail, key))
            raise ValueError(f"检测到 pack 依赖循环: {chain}")

        visiting.add(key)
        for dependency in catalog[key].depends_on:
            visit(dependency, (*trail, key))
        visiting.remove(key)
        visited.add(key)
        if key not in resolved:
            resolved.append(key)

    for key in pack_keys:
        visit(key, ())
    return tuple(resolved)


def _pack_definitions_for(pack_keys: tuple[str, ...], catalog: dict[str, PackDefinition]) -> tuple[PackDefinition, ...]:
    resolved_keys = _resolve_pack_keys(pack_keys, catalog)
    return tuple(catalog[key] for key in resolved_keys)


def validate_manifest(repo_root: Path, manifest: FocusManifest, catalog: dict[str, PackDefinition]) -> None:
    for key in REQUIRED_ENTRYPOINT_KEYS:
        command = manifest.entrypoints.get(key, "").strip()
        if not command:
            raise ValueError(f"`entrypoints.{key}` 不能为空。")

    if not manifest.packs:
        raise ValueError("`packs` 不能为空。")

    _resolve_pack_keys(manifest.packs, catalog)

    for relative_path in manifest.editable_paths:
        _validate_repo_path(repo_root, relative_path, "editable_paths")
    for relative_path in manifest.reference_paths:
        _validate_repo_path(repo_root, relative_path, "reference_paths")
    for relative_path in manifest.frozen_paths:
        _validate_repo_path(repo_root, relative_path, "frozen_paths")
    for selector in manifest.acceptance.test_selectors:
        _validate_selector(repo_root, selector, "acceptance.test_selectors")

    overlap = sorted(set(manifest.editable_paths) & set(manifest.frozen_paths))
    if overlap:
        raise ValueError(f"`editable_paths` 与 `frozen_paths` 存在冲突: {', '.join(overlap)}")


def _load_manifest_from_path(repo_root: Path, manifest_path: Path) -> FocusManifest:
    if not manifest_path.exists():
        raise FileNotFoundError(f"未找到 Focus Manifest: {manifest_path}")

    raw = _read_toml(manifest_path)
    strategy_raw = raw.get("strategy")
    cli_raw = raw.get("cli")
    entrypoints_raw = raw.get("entrypoints")
    acceptance_raw = raw.get("acceptance")

    if not isinstance(strategy_raw, dict):
        raise ValueError("Focus Manifest 缺少 `[strategy]` 段。")
    if not isinstance(cli_raw, dict):
        raise ValueError("Focus Manifest is missing the `[cli]` section.")
    if not isinstance(entrypoints_raw, dict):
        raise ValueError("Focus Manifest 缺少 `[entrypoints]` 段。")
    if not isinstance(acceptance_raw, dict):
        raise ValueError("Focus Manifest 缺少 `[acceptance]` 段。")

    manifest = FocusManifest(
        manifest_path=manifest_path,
        strategy=StrategyMetadata(
            name=_ensure_string(strategy_raw.get("name"), "strategy.name"),
            trading_target=_ensure_string(strategy_raw.get("trading_target"), "strategy.trading_target"),
            strategy_type=_ensure_string(strategy_raw.get("strategy_type"), "strategy.strategy_type"),
            run_mode=_ensure_string(strategy_raw.get("run_mode"), "strategy.run_mode"),
            summary=_ensure_string(strategy_raw.get("summary"), "strategy.summary"),
        ),
        packs=_ensure_string_tuple(raw.get("packs"), "packs"),
        cli=CliEntryMetadata(
            primary=_ensure_string(cli_raw.get("primary"), "cli.primary"),
            installed_alias=_ensure_string(cli_raw.get("installed_alias"), "cli.installed_alias"),
            cwd=_ensure_string(cli_raw.get("cwd"), "cli.cwd"),
        ),
        entrypoints={key: _ensure_string(entrypoints_raw.get(key), f"entrypoints.{key}") for key in REQUIRED_ENTRYPOINT_KEYS},
        editable_paths=_ensure_string_tuple(raw.get("editable_paths"), "editable_paths"),
        reference_paths=_ensure_string_tuple(raw.get("reference_paths"), "reference_paths"),
        frozen_paths=_ensure_string_tuple(raw.get("frozen_paths"), "frozen_paths"),
        acceptance=AcceptanceSpec(
            summary=_ensure_string(acceptance_raw.get("summary"), "acceptance.summary"),
            completion_checks=_ensure_string_tuple(acceptance_raw.get("completion_checks"), "acceptance.completion_checks"),
            minimal_test_command=_ensure_string(
                acceptance_raw.get("minimal_test_command"),
                "acceptance.minimal_test_command",
            ),
            test_selectors=_ensure_string_tuple(acceptance_raw.get("test_selectors"), "acceptance.test_selectors"),
            key_logs=_ensure_string_tuple(acceptance_raw.get("key_logs"), "acceptance.key_logs"),
            key_outputs=_ensure_string_tuple(acceptance_raw.get("key_outputs"), "acceptance.key_outputs"),
        ),
    )
    validate_manifest(repo_root, manifest, load_pack_catalog(repo_root))
    return manifest


def load_current_pointer(repo_root: Path) -> FocusPointer:
    pointer_path = current_pointer_path_for(repo_root)
    if not pointer_path.exists():
        raise FileNotFoundError(
            f"当前仓库尚未初始化策略焦点。请先执行 `{render_cli_command('focus init <strategy>')}`。"
        )

    raw = _read_toml(pointer_path)
    strategy = _ensure_string(raw.get("strategy"), "current.strategy")
    manifest_relative_path = _ensure_string(raw.get("manifest_path"), "current.manifest_path")
    manifest_path = repo_root / manifest_relative_path
    if not manifest_path.exists():
        raise FileNotFoundError(f"当前焦点引用的 Manifest 不存在: {manifest_relative_path}")
    return FocusPointer(strategy=strategy, manifest_path=manifest_path)


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_current_pointer(repo_root: Path, strategy_name: str, manifest_path: Path) -> FocusPointer:
    relative_manifest_path = manifest_path.relative_to(repo_root).as_posix()
    content = "\n".join(
        [
            f"strategy = {_quote(slugify(strategy_name))}",
            f"manifest_path = {_quote(relative_manifest_path)}",
            "",
        ]
    )
    path = current_pointer_path_for(repo_root)
    _write(path, content)
    return FocusPointer(strategy=slugify(strategy_name), manifest_path=manifest_path)


def _default_entrypoints() -> dict[str, str]:
    return {
        "run": render_cli_command("run --config config/strategy_config.toml --paper"),
        "backtest": render_cli_command(
            "backtest --config config/strategy_config.toml --start 2025-01-01 --end 2025-03-01 --no-chart"
        ),
        "validate": render_cli_command("validate --config config/strategy_config.toml"),
        "monitor": "python src/web/app.py",
    }


def _default_acceptance(
    *,
    summary: str | None = None,
    completion_checks: tuple[str, ...] | None = None,
) -> AcceptanceSpec:
    return AcceptanceSpec(
        summary=summary or "Focus navigation, current context, and validation outputs stay aligned for AGENT-driven edits.",
        completion_checks=completion_checks
        or (
            "Focus navigation files are refreshed and point to the current manifest.",
            "Validation succeeds for the current strategy configuration.",
            "Focus verification succeeds for the current strategy.",
        ),
        minimal_test_command=render_cli_command("focus test"),
        test_selectors=(
            "tests/main/focus",
            "tests/cli/test_app.py",
        ),
        key_logs=(
            "Validation passed",
            "Doctor completed",
            "Focus assets refreshed",
        ),
        key_outputs=(
            ".focus/SYSTEM_MAP.md",
            ".focus/ACTIVE_SURFACE.md",
            ".focus/TASK_BRIEF.md",
            ".focus/COMMANDS.md",
            ".focus/TASK_ROUTER.md",
            ".focus/TEST_MATRIX.md",
            ".focus/context.json",
        ),
    )


def _render_manifest(manifest: FocusManifest) -> str:
    entrypoint_lines = "\n".join(f"{key} = {_quote(value)}" for key, value in manifest.entrypoints.items())
    return "\n".join(
        [
            f"packs = [{', '.join(_quote(item) for item in manifest.packs)}]",
            f"editable_paths = [{', '.join(_quote(item) for item in manifest.editable_paths)}]",
            f"reference_paths = [{', '.join(_quote(item) for item in manifest.reference_paths)}]",
            f"frozen_paths = [{', '.join(_quote(item) for item in manifest.frozen_paths)}]",
            "",
            "[strategy]",
            f"name = {_quote(manifest.strategy.name)}",
            f"trading_target = {_quote(manifest.strategy.trading_target)}",
            f"strategy_type = {_quote(manifest.strategy.strategy_type)}",
            f"run_mode = {_quote(manifest.strategy.run_mode)}",
            f"summary = {_quote(manifest.strategy.summary)}",
            "",
            "[cli]",
            f"primary = {_quote(manifest.cli.primary)}",
            f"installed_alias = {_quote(manifest.cli.installed_alias)}",
            f"cwd = {_quote(manifest.cli.cwd)}",
            "",
            "[entrypoints]",
            entrypoint_lines,
            "",
            "[acceptance]",
            f"summary = {_quote(manifest.acceptance.summary)}",
            (
                "completion_checks = ["
                + ", ".join(_quote(item) for item in manifest.acceptance.completion_checks)
                + "]"
            ),
            f"minimal_test_command = {_quote(manifest.acceptance.minimal_test_command)}",
            (
                "test_selectors = ["
                + ", ".join(_quote(item) for item in manifest.acceptance.test_selectors)
                + "]"
            ),
            f"key_logs = [{', '.join(_quote(item) for item in manifest.acceptance.key_logs)}]",
            f"key_outputs = [{', '.join(_quote(item) for item in manifest.acceptance.key_outputs)}]",
            "",
        ]
    )


def _build_default_manifest(
    repo_root: Path,
    strategy_name: str,
    *,
    trading_target: str,
    strategy_type: str,
    run_mode: str,
    pack_keys: tuple[str, ...],
) -> FocusManifest:
    slug = slugify(strategy_name)
    manifest_path = manifest_path_for(repo_root, strategy_name)
    return FocusManifest(
        manifest_path=manifest_path,
        strategy=StrategyMetadata(
            name=slug,
            trading_target=trading_target,
            strategy_type=strategy_type,
            run_mode=run_mode,
            summary="Default full-pack focus for AGENT-driven strategy development in the current repository.",
        ),
        packs=pack_keys,
        cli=get_cli_entry_metadata(),
        entrypoints=_default_entrypoints(),
        editable_paths=DEFAULT_EDITABLE_PATHS,
        reference_paths=DEFAULT_REFERENCE_PATHS,
        frozen_paths=DEFAULT_FROZEN_PATHS,
        acceptance=_default_acceptance(),
    )


def _default_acceptance_v2(
    *,
    summary: str | None = None,
    completion_checks: tuple[str, ...] | None = None,
) -> AcceptanceSpec:
    return AcceptanceSpec(
        summary=summary or "Focus navigation, current context, and validation outputs stay aligned for AGENT-driven edits.",
        completion_checks=completion_checks
        or (
            "Focus navigation files are refreshed and point to the current manifest.",
            "Validation succeeds for the current strategy configuration.",
            "Focus verification succeeds for the current strategy.",
        ),
        minimal_test_command=render_cli_command("focus test"),
        test_selectors=(
            "tests/main/focus",
            "tests/cli/test_app.py",
        ),
        key_logs=(
            "Validation passed",
            "Doctor completed",
            "Focus assets refreshed",
        ),
        key_outputs=(
            ".focus/SYSTEM_MAP.md",
            ".focus/ACTIVE_SURFACE.md",
            ".focus/TASK_BRIEF.md",
            ".focus/COMMANDS.md",
            ".focus/TASK_ROUTER.md",
            ".focus/TEST_MATRIX.md",
            ".focus/context.json",
        ),
    )


def _build_default_manifest_v2(
    repo_root: Path,
    strategy_name: str,
    *,
    trading_target: str,
    strategy_type: str,
    run_mode: str,
    pack_keys: tuple[str, ...],
    summary: str | None = None,
    completion_checks: tuple[str, ...] | None = None,
) -> FocusManifest:
    slug = slugify(strategy_name)
    manifest_path = manifest_path_for(repo_root, strategy_name)
    frozen_paths = tuple(path for path in DEFAULT_FROZEN_PATHS if (repo_root / path).exists())
    return FocusManifest(
        manifest_path=manifest_path,
        strategy=StrategyMetadata(
            name=slug,
            trading_target=trading_target,
            strategy_type=strategy_type,
            run_mode=run_mode,
            summary=summary or "Default full-pack focus for AGENT-driven strategy development in the current repository.",
        ),
        packs=pack_keys,
        cli=get_cli_entry_metadata(),
        entrypoints=_default_entrypoints(),
        editable_paths=DEFAULT_EDITABLE_PATHS,
        reference_paths=DEFAULT_REFERENCE_PATHS,
        frozen_paths=frozen_paths,
        acceptance=_default_acceptance_v2(summary=summary, completion_checks=completion_checks),
    )


def _unique_preserve_order(items: Iterable[str]) -> tuple[str, ...]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        result.append(item)
    return tuple(result)


def focus_test_command(*, full: bool = False) -> str:
    return render_cli_command("focus test --full" if full else "focus test")


def _smoke_keyword_expression() -> str:
    return " and ".join(f"not {keyword}" for keyword in SMOKE_TEST_EXCLUDE_KEYWORDS)


def _smoke_filter_descriptions() -> tuple[str, ...]:
    return tuple(
        f"Exclude test nodes whose names contain `{keyword}`."
        for keyword in SMOKE_TEST_EXCLUDE_KEYWORDS
    )


def _collect_commands(context: FocusContext) -> tuple[str, ...]:
    commands = [
        context.manifest.entrypoints["validate"],
        context.manifest.entrypoints["run"],
        context.manifest.entrypoints["backtest"],
        context.manifest.entrypoints["monitor"],
        context.manifest.acceptance.minimal_test_command,
    ]
    for pack in context.resolved_packs:
        commands.extend(pack.commands)
    return _unique_preserve_order(commands)


def build_focus_context_payload(context: FocusContext) -> dict[str, object]:
    recommended_pack, first_entry = build_recommended_first_pass(context)
    test_matrix = build_focus_test_matrix(context)
    generated_docs = {
        "system_map": context.system_map_path.relative_to(context.repo_root).as_posix(),
        "active_surface": context.active_surface_path.relative_to(context.repo_root).as_posix(),
        "task_brief": context.task_brief_path.relative_to(context.repo_root).as_posix(),
        "commands": context.commands_path.relative_to(context.repo_root).as_posix(),
        "task_router": context.task_router_path.relative_to(context.repo_root).as_posix(),
        "test_matrix": context.test_matrix_path.relative_to(context.repo_root).as_posix(),
        "context_json": context.context_json_path.relative_to(context.repo_root).as_posix(),
    }
    return {
        "strategy": {
            "name": context.manifest.strategy.name,
            "trading_target": context.manifest.strategy.trading_target,
            "strategy_type": context.manifest.strategy.strategy_type,
            "run_mode": context.manifest.strategy.run_mode,
            "summary": context.manifest.strategy.summary,
        },
        "manifest_path": context.manifest.manifest_path.relative_to(context.repo_root).as_posix(),
        "packs": [pack.key for pack in context.resolved_packs],
        "cli": cli_entry_metadata_payload(context.manifest.cli),
        "recommended_first_pass": {
            "pack": recommended_pack,
            "entry": first_entry,
        },
        "entrypoints": dict(context.manifest.entrypoints),
        "surfaces": {
            "editable": list(context.manifest.editable_paths),
            "reference": list(context.manifest.reference_paths),
            "frozen": list(context.manifest.frozen_paths),
        },
        "health": list(describe_focus_health(context)),
        "test_matrix": {
            "smoke_selectors": list(test_matrix.smoke_selectors),
            "full_selectors": list(test_matrix.full_selectors),
            "smoke_keyword_expression": test_matrix.smoke_keyword_expression,
            "smoke_filter_descriptions": list(test_matrix.smoke_filter_descriptions),
            "skipped_packs": [
                {
                    "pack_key": item.pack_key,
                    "missing_modules": list(item.missing_modules),
                }
                for item in test_matrix.skipped_packs
            ],
        },
        "generated_docs": generated_docs,
        "acceptance": {
            "summary": context.manifest.acceptance.summary,
            "completion_checks": list(context.manifest.acceptance.completion_checks),
            "minimal_test_command": context.manifest.acceptance.minimal_test_command,
            "test_selectors": list(context.manifest.acceptance.test_selectors),
            "key_logs": list(context.manifest.acceptance.key_logs),
            "key_outputs": list(context.manifest.acceptance.key_outputs),
        },
    }


def build_focus_test_matrix(context: FocusContext) -> FocusTestMatrix:
    selectors: list[str] = list(context.manifest.acceptance.test_selectors)
    skipped_packs: list[SkippedPackTests] = []

    for pack in context.resolved_packs:
        required_modules = PACK_REQUIRED_MODULES.get(pack.key, ())
        missing_modules = tuple(module_name for module_name in required_modules if not _module_available(module_name))
        if missing_modules:
            skipped_packs.append(SkippedPackTests(pack_key=pack.key, missing_modules=missing_modules))
            continue
        selectors.extend(pack.test_selectors)

    full_selectors = _unique_preserve_order(selectors)
    return FocusTestMatrix(
        smoke_selectors=full_selectors,
        full_selectors=full_selectors,
        skipped_packs=tuple(skipped_packs),
        smoke_keyword_expression=_smoke_keyword_expression(),
        smoke_filter_descriptions=_smoke_filter_descriptions(),
    )


def collect_test_selectors(context: FocusContext) -> tuple[str, ...]:
    selectors: list[str] = list(context.manifest.acceptance.test_selectors)
    for pack in context.resolved_packs:
        selectors.extend(pack.test_selectors)
    return _unique_preserve_order(selectors)


def collect_runnable_test_selectors(context: FocusContext) -> tuple[tuple[str, ...], tuple[tuple[str, tuple[str, ...]], ...]]:
    test_matrix = build_focus_test_matrix(context)
    skipped_packs = tuple(
        (skipped_pack.pack_key, skipped_pack.missing_modules)
        for skipped_pack in test_matrix.skipped_packs
    )
    return test_matrix.full_selectors, skipped_packs


def _module_available(module_name: str) -> bool:
    try:
        importlib.import_module(module_name)
    except ModuleNotFoundError:
        return False
    return True


def describe_focus_health(context: FocusContext) -> tuple[str, ...]:
    pack_count = len(context.resolved_packs)
    editable_path_count = len(context.manifest.editable_paths)
    summary = f"Focus width: {pack_count} packs and {editable_path_count} editable-surface entries."

    if pack_count >= WIDE_FOCUS_PACK_THRESHOLD or editable_path_count >= WIDE_FOCUS_EDITABLE_THRESHOLD:
        return (
            summary,
            "This focus is wide. Start from the TASK_ROUTER first-pass entry instead of scanning everything.",
        )
    return (
        summary,
        "This focus is narrow enough to start directly from the recommended first pass.",
    )


def _render_navigation(context: FocusContext) -> None:
    (
        system_map_path,
        active_surface_path,
        task_brief_path,
        commands_path,
        task_router_path,
        test_matrix_path,
    ) = _generated_doc_paths(context.repo_root)
    commands = _collect_commands(context)
    test_matrix = build_focus_test_matrix(context)
    smoke_test_command = focus_test_command()
    full_test_command = focus_test_command(full=True)
    _write(system_map_path, render_system_map(context))
    _write(active_surface_path, render_active_surface(context))
    _write(task_brief_path, render_task_brief(context))
    _write(
        commands_path,
        render_commands(
            context,
            commands,
            smoke_test_command=smoke_test_command,
            full_test_command=full_test_command,
        ),
    )
    _write(
        task_router_path,
        render_task_router(
            context,
            test_matrix,
            smoke_test_command=smoke_test_command,
            full_test_command=full_test_command,
        ),
    )
    _write(
        test_matrix_path,
        render_test_matrix(
            context,
            test_matrix,
            smoke_test_command=smoke_test_command,
            full_test_command=full_test_command,
        ),
    )
    _write_json(context.context_json_path, build_focus_context_payload(context))


def load_focus_context(repo_root: Path, strategy_name: str | None = None) -> FocusContext:
    catalog = load_pack_catalog(repo_root)
    pointer = load_current_pointer(repo_root) if strategy_name is None else FocusPointer(
        strategy=slugify(strategy_name),
        manifest_path=manifest_path_for(repo_root, strategy_name),
    )
    manifest = _load_manifest_from_path(repo_root, pointer.manifest_path)
    resolved_packs = _pack_definitions_for(manifest.packs, catalog)
    return FocusContext(
        repo_root=repo_root,
        pointer=FocusPointer(strategy=manifest.strategy.name, manifest_path=manifest.manifest_path),
        manifest=manifest,
        resolved_packs=resolved_packs,
    )


def initialize_focus(
    repo_root: Path,
    strategy_name: str,
    *,
    trading_target: str,
    strategy_type: str,
    run_mode: str,
    include_packs: tuple[str, ...] = (),
    exclude_packs: tuple[str, ...] = (),
    force: bool = False,
    summary: str | None = None,
    completion_checks: tuple[str, ...] | None = None,
) -> FocusContext:
    catalog = load_pack_catalog(repo_root)
    selected = include_packs or tuple(key for key in DEFAULT_PACK_KEYS if key in catalog)
    selected = tuple(key for key in selected if key not in set(exclude_packs))
    if not selected:
        raise ValueError("初始化策略焦点时至少需要保留一个 pack。")
    resolved_pack_keys = _resolve_pack_keys(selected, catalog)
    manifest = _build_default_manifest_v2(
        repo_root,
        strategy_name,
        trading_target=trading_target,
        strategy_type=strategy_type,
        run_mode=run_mode,
        pack_keys=resolved_pack_keys,
        summary=summary,
        completion_checks=completion_checks,
    )
    if manifest.manifest_path.exists() and not force:
        relative_path = manifest.manifest_path.relative_to(repo_root).as_posix()
        raise FileExistsError(f"Focus Manifest 已存在: {relative_path}。如需覆盖请使用 `--force`。")

    validate_manifest(repo_root, manifest, catalog)
    _write(manifest.manifest_path, _render_manifest(manifest))
    write_current_pointer(repo_root, strategy_name, manifest.manifest_path)
    context = load_focus_context(repo_root, strategy_name)
    _render_navigation(context)
    return context


def refresh_focus(repo_root: Path, strategy_name: str | None = None) -> FocusContext:
    context = load_focus_context(repo_root, strategy_name)
    write_current_pointer(repo_root, context.manifest.strategy.name, context.manifest.manifest_path)
    _render_navigation(context)
    return context


def _merge_keyword_expression(extra_args: tuple[str, ...], expression: str) -> tuple[str, ...]:
    args = list(extra_args)
    for index, argument in enumerate(args):
        if argument == "-k" and index + 1 < len(args):
            args[index + 1] = f"({args[index + 1]}) and ({expression})"
            return tuple(args)
        if argument.startswith("-k="):
            args[index] = f"-k=({argument[3:]}) and ({expression})"
            return tuple(args)
        if argument == "--keyword" and index + 1 < len(args):
            args[index + 1] = f"({args[index + 1]}) and ({expression})"
            return tuple(args)
        if argument.startswith("--keyword="):
            args[index] = f"--keyword=({argument[len('--keyword='):]}) and ({expression})"
            return tuple(args)
    return ("-k", expression, *extra_args)


def run_focus_tests(
    repo_root: Path,
    strategy_name: str | None = None,
    extra_args: tuple[str, ...] = (),
    *,
    full: bool = False,
) -> int:
    context = load_focus_context(repo_root, strategy_name)
    test_matrix = build_focus_test_matrix(context)
    selectors = test_matrix.full_selectors if full else test_matrix.smoke_selectors
    if not selectors:
        raise ValueError("当前策略焦点没有可运行的测试选择器。")

    try:
        import pytest
    except ModuleNotFoundError as exc:
        raise ModuleNotFoundError("缺少 pytest，请先安装测试依赖。") from exc

    config_path = repo_root / "config" / "pytest.ini"
    args: list[str] = []
    if config_path.exists():
        args.extend(["-c", str(config_path)])
    args.extend(selectors)
    effective_extra_args = extra_args
    if not full:
        effective_extra_args = _merge_keyword_expression(
            extra_args,
            test_matrix.smoke_keyword_expression,
        )
    args.extend(effective_extra_args)
    result = pytest.main(args)
    return int(result)
