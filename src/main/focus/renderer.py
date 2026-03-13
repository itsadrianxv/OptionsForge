from __future__ import annotations

from src.cli.common import render_cli_command

from .models import FocusContext, FocusTestMatrix, PackDefinition

PACK_TASK_LABELS: dict[str, str] = {
    "kernel": "Core runtime flow and focus entrypoint",
    "selection": "Underlying and contract selection",
    "pricing": "Pricing and Greeks computation",
    "risk": "Portfolio risk and limits",
    "execution": "Order execution and scheduling",
    "hedging": "Delta and Vega hedging",
    "monitoring": "Monitoring, persistence, and observability",
    "web": "Read-only visual monitoring",
    "deploy": "Container and environment setup",
    "backtest": "Backtest flow and parameter verification",
}
FIRST_PASS_PACK_PRIORITY: tuple[str, ...] = (
    "selection",
    "pricing",
    "risk",
    "execution",
    "hedging",
    "monitoring",
    "web",
    "backtest",
    "deploy",
    "kernel",
)
COMMON_MISTAKE_PREFIX = "Common mistake: "


def _render_paths(paths: tuple[str, ...], *, indent: str = "") -> list[str]:
    if not paths:
        return [f"{indent}- none"]
    return [f"{indent}- `{path}`" for path in paths]


def _render_text_items(items: tuple[str, ...], *, indent: str = "") -> list[str]:
    if not items:
        return [f"{indent}- none"]
    return [f"{indent}- {item}" for item in items]


def _unique_preserve_order(items: tuple[str, ...]) -> tuple[str, ...]:
    result: list[str] = []
    seen: set[str] = set()
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        result.append(item)
    return tuple(result)


def _task_label(pack: PackDefinition) -> str:
    return PACK_TASK_LABELS.get(pack.key, pack.key)


def _pack_code_paths(pack: PackDefinition) -> tuple[str, ...]:
    source_paths = tuple(path for path in pack.owned_paths if path.startswith("src/"))
    if source_paths:
        return source_paths

    non_test_paths = tuple(path for path in pack.owned_paths if not path.startswith("tests/"))
    if non_test_paths:
        return non_test_paths

    return pack.owned_paths


def _pack_config_paths(pack: PackDefinition) -> tuple[str, ...]:
    config_paths = tuple(
        path
        for path in pack.owned_paths
        if path.startswith("config/") or path.startswith("deploy/") or path.endswith(".env") or path.endswith(".env.example")
    )
    if config_paths:
        return _unique_preserve_order(config_paths)
    if pack.config_keys:
        return ("config/strategy_config.toml",)
    return ()


def _pack_common_mistakes(pack: PackDefinition) -> tuple[str, ...]:
    explicit = tuple(
        note.split(COMMON_MISTAKE_PREFIX, 1)[1].strip()
        for note in pack.agent_notes
        if note.startswith(COMMON_MISTAKE_PREFIX)
    )
    if explicit:
        return explicit
    if pack.agent_notes:
        return (pack.agent_notes[-1],)
    return ()


def _pack_agent_notes(pack: PackDefinition) -> tuple[str, ...]:
    return tuple(note for note in pack.agent_notes if not note.startswith(COMMON_MISTAKE_PREFIX))


def build_recommended_first_pass(context: FocusContext) -> tuple[str, str]:
    packs_by_key = {pack.key: pack for pack in context.resolved_packs}
    for key in FIRST_PASS_PACK_PRIORITY:
        if key in packs_by_key:
            selected_pack = packs_by_key[key]
            break
    else:
        selected_pack = context.resolved_packs[0]

    first_entry_candidates = _pack_code_paths(selected_pack)
    if first_entry_candidates:
        return selected_pack.key, first_entry_candidates[0]
    if context.manifest.editable_paths:
        return selected_pack.key, context.manifest.editable_paths[0]
    return selected_pack.key, selected_pack.owned_paths[0]


def _render_pack(pack: PackDefinition) -> list[str]:
    dependencies = ", ".join(f"`{item}`" for item in pack.depends_on) if pack.depends_on else "none"
    config_keys = ", ".join(f"`{item}`" for item in pack.config_keys) if pack.config_keys else "none"
    lines = [
        f"### `{pack.key}`",
        "",
        f"- Depends on: {dependencies}",
        f"- Config keys: {config_keys}",
        "- Owned paths:",
        *_render_paths(pack.owned_paths),
        "- Common commands:",
    ]
    if pack.commands:
        lines.extend(f"  - `{item}`" for item in pack.commands)
    else:
        lines.append("  - none")
    lines.append("- Agent notes:")
    if pack.agent_notes:
        lines.extend(f"  - {item}" for item in pack.agent_notes)
    else:
        lines.append("  - none")
    return lines


def render_system_map(context: FocusContext) -> str:
    pack_chain = " -> ".join(f"`{pack.key}`" for pack in context.resolved_packs)
    manifest_path = context.pointer.manifest_path.relative_to(context.repo_root).as_posix()
    lines = [
        "# SYSTEM MAP",
        "",
        "## Current Focus",
        "",
        f"- Strategy: `{context.manifest.strategy.name}`",
        f"- Trading target: `{context.manifest.strategy.trading_target}`",
        f"- Strategy type: `{context.manifest.strategy.strategy_type}`",
        f"- Run mode: `{context.manifest.strategy.run_mode}`",
        f"- Focus Manifest: `{manifest_path}`",
        f"- Pack chain: {pack_chain}",
        "",
        "## Read In This Order",
        "",
        f"1. `{manifest_path}`",
        f"2. `{context.manifest.editable_paths[0]}`",
        f"3. `{context.manifest.editable_paths[1]}`",
        f"4. `{context.manifest.editable_paths[2]}`",
        f"5. `{context.manifest.editable_paths[3]}`",
        "",
        "## Runtime Chain",
        "",
        f"1. Source-checkout default: `{context.manifest.cli.primary}`.",
        f"2. Installed alias: `{context.manifest.cli.installed_alias}`.",
        f"3. Run CLI commands from `{context.manifest.cli.cwd}`.",
        "4. `src/cli/app.py` routes commands to `forge`, `focus`, `run`, `backtest`, `validate`, and supporting commands.",
        "5. `src/main/main.py` orchestrates runtime startup.",
        "6. `src/strategy/strategy_entry.py` connects application, domain, and infrastructure layers.",
        "7. Enabled packs extend the runtime with domain logic, monitoring, backtest, web, and deploy capabilities.",
        "",
        "## Pack Notes",
        "",
    ]
    for index, pack in enumerate(context.resolved_packs):
        lines.extend(_render_pack(pack))
        if index != len(context.resolved_packs) - 1:
            lines.append("")
    return "\n".join(lines) + "\n"


def render_active_surface(context: FocusContext) -> str:
    lines = [
        "# ACTIVE SURFACE",
        "",
        "## Editable Surface",
        "",
        *_render_paths(context.manifest.editable_paths),
        "",
        "## Reference Surface",
        "",
        *_render_paths(context.manifest.reference_paths),
        "",
        "## Frozen Surface",
        "",
        *_render_paths(context.manifest.frozen_paths),
    ]
    return "\n".join(lines) + "\n"


def render_task_brief(context: FocusContext) -> str:
    lines = [
        "# TASK BRIEF",
        "",
        "## Summary",
        "",
        f"- {context.manifest.strategy.summary}",
        f"- Current trading target: `{context.manifest.strategy.trading_target}`",
        f"- Current run mode: `{context.manifest.strategy.run_mode}`",
        "- Default rule: stay inside the editable surface unless there is a concrete reason to expand scope.",
        "",
        "## Recommended Edit Entrypoints",
        "",
        *_render_paths(context.manifest.editable_paths[:6]),
        "",
        "## Do Not Edit",
        "",
        *_render_paths(context.manifest.frozen_paths),
        "",
        "## Acceptance",
        "",
        f"- Summary: {context.manifest.acceptance.summary}",
        f"- Minimal verification command: `{context.manifest.acceptance.minimal_test_command}`",
        *[f"- {item}" for item in context.manifest.acceptance.completion_checks],
        "",
        "## Key Logs And Outputs",
        "",
        "### Key Logs",
        "",
        *_render_paths(context.manifest.acceptance.key_logs),
        "",
        "### Key Outputs",
        "",
        *_render_paths(context.manifest.acceptance.key_outputs),
    ]
    return "\n".join(lines) + "\n"


def render_task_router(
    context: FocusContext,
    test_matrix: FocusTestMatrix,
    *,
    smoke_test_command: str,
    full_test_command: str,
) -> str:
    del test_matrix
    lines = [
        "# TASK ROUTER",
        "",
        "## How To Use This File",
        "",
        "- Match the task to the closest pack first, then start from the recommended entrypoint.",
        f"- Default verification order: `{smoke_test_command}` first, then `{full_test_command}` only when needed.",
        "- If the current focus is wide, start from one pack instead of scanning the full editable surface.",
        "",
    ]

    for index, pack in enumerate(context.resolved_packs):
        code_paths = _pack_code_paths(pack)
        config_paths = _pack_config_paths(pack)
        common_mistakes = _pack_common_mistakes(pack)
        extra_notes = _pack_agent_notes(pack)
        config_keys = ", ".join(f"`{item}`" for item in pack.config_keys) if pack.config_keys else "none"

        lines.extend(
            [
                f"### `{pack.key}`",
                "",
                f"- Task type: {_task_label(pack)}",
                "- Read first:",
                *_render_paths(code_paths, indent="  "),
                "- Related config:",
                *_render_paths(config_paths, indent="  "),
                f"  - Config keys: {config_keys}",
                "- Recommended verification:",
                f"  - Smoke: `{smoke_test_command}`",
                "  - Relevant selectors:",
                *_render_paths(pack.test_selectors, indent="    "),
                f"  - Full: `{full_test_command}`",
                "- Common commands:",
                *_render_paths(pack.commands, indent="  "),
                "- Common mistakes:",
                *_render_text_items(common_mistakes, indent="  "),
                "- Agent notes:",
                *_render_text_items(extra_notes, indent="  "),
            ]
        )
        if index != len(context.resolved_packs) - 1:
            lines.append("")

    return "\n".join(lines) + "\n"


def render_test_matrix(
    context: FocusContext,
    test_matrix: FocusTestMatrix,
    *,
    smoke_test_command: str,
    full_test_command: str,
) -> str:
    lines = [
        "# TEST MATRIX",
        "",
        "## Smoke",
        "",
        f"- Command: `{smoke_test_command}`",
        "- Notes: smoke uses the same selectors as full mode, plus keyword filters.",
        "- Selectors:",
        *_render_paths(test_matrix.smoke_selectors, indent="  "),
        "- Keyword filters:",
        *_render_text_items(test_matrix.smoke_filter_descriptions, indent="  "),
        "",
        "## Full",
        "",
        f"- Command: `{full_test_command}`",
        "- Selectors:",
        *_render_paths(test_matrix.full_selectors, indent="  "),
        "",
        "## Skipped Packs",
        "",
    ]

    if test_matrix.skipped_packs:
        for skipped_pack in test_matrix.skipped_packs:
            missing_modules = ", ".join(f"`{item}`" for item in skipped_pack.missing_modules)
            lines.append(f"- `{skipped_pack.pack_key}`: missing dependency {missing_modules}")
    else:
        lines.append("- none")

    return "\n".join(lines) + "\n"


def render_commands(
    context: FocusContext,
    commands: tuple[str, ...],
    *,
    smoke_test_command: str,
    full_test_command: str,
) -> str:
    lines = [
        "# COMMANDS",
        "",
        "## Focus Commands",
        "",
        f"- `{render_cli_command('forge', metadata=context.manifest.cli)}`",
        f"- `{render_cli_command('focus show', metadata=context.manifest.cli)}`",
        f"- `{render_cli_command('focus refresh', metadata=context.manifest.cli)}`",
        f"- `{smoke_test_command}`",
        f"- `{full_test_command}`",
        "",
        "## Verification Modes",
        "",
        "- `smoke`: excludes test nodes with `property` or `pbt` in the name.",
        "- `full`: runs the complete runnable selector set for the current focus.",
        "",
        "## Current Strategy Commands",
        "",
        *[f"- `{item}`" for item in commands],
    ]
    return "\n".join(lines) + "\n"
