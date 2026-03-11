from __future__ import annotations

from .models import FocusContext, FocusTestMatrix, PackDefinition

PACK_TASK_LABELS: dict[str, str] = {
    "kernel": "主运行链路与焦点入口",
    "selection": "选标与合约筛选",
    "pricing": "定价与 Greeks 计算",
    "risk": "组合风控与限额控制",
    "execution": "下单执行与排程",
    "hedging": "Delta / Vega 对冲",
    "monitoring": "监控、日志与状态落盘",
    "web": "可视化展示与快照读取",
    "deploy": "容器化与环境装配",
    "backtest": "回测链路与参数验证",
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


def _render_paths(paths: tuple[str, ...], *, indent: str = "") -> list[str]:
    if not paths:
        return [f"{indent}- 无"]
    return [f"{indent}- `{path}`" for path in paths]


def _render_text_items(items: tuple[str, ...], *, indent: str = "") -> list[str]:
    if not items:
        return [f"{indent}- 无"]
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
        note.split("常见误改：", 1)[1].strip()
        for note in pack.agent_notes
        if note.startswith("常见误改：")
    )
    if explicit:
        return explicit
    if pack.agent_notes:
        return (pack.agent_notes[-1],)
    return ()


def _pack_agent_notes(pack: PackDefinition) -> tuple[str, ...]:
    return tuple(note for note in pack.agent_notes if not note.startswith("常见误改："))


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
    dependencies = ", ".join(f"`{item}`" for item in pack.depends_on) if pack.depends_on else "无"
    config_keys = ", ".join(f"`{item}`" for item in pack.config_keys) if pack.config_keys else "无"
    lines = [
        f"### `{pack.key}`",
        "",
        f"- 依赖: {dependencies}",
        f"- 配置键: {config_keys}",
        "- 所属路径:",
        *_render_paths(pack.owned_paths),
        "- 常用命令:",
    ]
    if pack.commands:
        lines.extend(f"  - `{item}`" for item in pack.commands)
    else:
        lines.append("  - 无")
    lines.append("- Agent 提示:")
    if pack.agent_notes:
        lines.extend(f"  - {item}" for item in pack.agent_notes)
    else:
        lines.append("  - 无")
    return lines


def render_system_map(context: FocusContext) -> str:
    pack_chain = " -> ".join(f"`{pack.key}`" for pack in context.resolved_packs)
    manifest_path = context.pointer.manifest_path.relative_to(context.repo_root).as_posix()
    lines = [
        "# SYSTEM MAP",
        "",
        "## Current Focus",
        "",
        f"- 策略: `{context.manifest.strategy.name}`",
        f"- 交易标的: `{context.manifest.strategy.trading_target}`",
        f"- 策略类型: `{context.manifest.strategy.strategy_type}`",
        f"- 运行模式: `{context.manifest.strategy.run_mode}`",
        f"- Focus Manifest: `{manifest_path}`",
        f"- Pack 链路: {pack_chain}",
        "",
        "## 建议阅读顺序",
        "",
        f"1. `{manifest_path}`",
        f"2. `{context.manifest.editable_paths[0]}`",
        f"3. `{context.manifest.editable_paths[1]}`",
        f"4. `{context.manifest.editable_paths[2]}`",
        f"5. `{context.manifest.editable_paths[3]}`",
        "",
        "## 运行链路",
        "",
        "1. `option-scaffold` / `option-scaffold focus` 作为统一入口",
        "2. `src/cli/app.py` 把命令分发到 `run`、`backtest`、`validate` 与 `focus`",
        "3. `src/main/main.py` 负责主运行链路与启动编排",
        "4. `src/strategy/strategy_entry.py` 连接 application / domain / infrastructure",
        "5. 当前启用 pack 在领域服务、监控、回测、Web 与部署侧补齐能力",
        "",
        "## Pack 说明",
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
        "## Support Surface",
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
        "## 需求摘要",
        "",
        f"- {context.manifest.strategy.summary}",
        (
            f"- 当前策略聚焦 `{context.manifest.strategy.trading_target}`，"
            f"按 `{context.manifest.strategy.run_mode}` 运行"
        ),
        "- 默认优先在 Editable Surface 内完成改动，只有确有必要时再扩展焦点",
        "",
        "## 首选修改入口",
        "",
        *_render_paths(context.manifest.editable_paths[:6]),
        "",
        "## 禁止改动边界",
        "",
        *_render_paths(context.manifest.frozen_paths),
        "",
        "## 验收要求",
        "",
        f"- 概述: {context.manifest.acceptance.summary}",
        f"- 最小测试命令: `{context.manifest.acceptance.minimal_test_command}`",
        *[f"- {item}" for item in context.manifest.acceptance.completion_checks],
        "",
        "## 关键日志 / 产物",
        "",
        "### 关键日志",
        "",
        *_render_paths(context.manifest.acceptance.key_logs),
        "",
        "### 关键产物",
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
        "## 使用方式",
        "",
        "- 先匹配最接近的任务类型，再按首看入口进入代码。",
        f"- 默认先跑 `{smoke_test_command}`，通过后再补跑 `{full_test_command}`。",
        "- 如果当前焦点偏宽，先从单个 pack 开始，不要一上来横扫整个 Editable Surface。",
        "",
    ]

    for index, pack in enumerate(context.resolved_packs):
        code_paths = _pack_code_paths(pack)
        config_paths = _pack_config_paths(pack)
        common_mistakes = _pack_common_mistakes(pack)
        extra_notes = _pack_agent_notes(pack)
        config_keys = ", ".join(f"`{item}`" for item in pack.config_keys) if pack.config_keys else "无"

        lines.extend(
            [
                f"### `{pack.key}`",
                "",
                f"- 任务类型: {_task_label(pack)}",
                "- 首看入口:",
                *_render_paths(code_paths, indent="  "),
                "- 相关配置:",
                *_render_paths(config_paths, indent="  "),
                f"  - 配置键: {config_keys}",
                "- 推荐测试:",
                f"  - Smoke: `{smoke_test_command}`",
                "  - 相关选择器:",
                *_render_paths(pack.test_selectors, indent="    "),
                f"  - Full: `{full_test_command}`",
                "- 常用命令:",
                *_render_paths(pack.commands, indent="  "),
                "- 常见误改:",
                *_render_text_items(common_mistakes, indent="  "),
                "- Agent 提示:",
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
    del context
    lines = [
        "# TEST MATRIX",
        "",
        "## Smoke",
        "",
        f"- 命令: `{smoke_test_command}`",
        "- 说明: 与 Full 使用同一组 selectors，但额外应用节点级过滤。",
        "- 选择器:",
        *_render_paths(test_matrix.smoke_selectors, indent="  "),
        "- 节点过滤:",
        *_render_text_items(test_matrix.smoke_filter_descriptions, indent="  "),
        "",
        "## Full",
        "",
        f"- 命令: `{full_test_command}`",
        "- 选择器:",
        *_render_paths(test_matrix.full_selectors, indent="  "),
        "",
        "## Skipped Packs",
        "",
    ]

    if test_matrix.skipped_packs:
        for skipped_pack in test_matrix.skipped_packs:
            missing_modules = ", ".join(f"`{item}`" for item in skipped_pack.missing_modules)
            lines.append(f"- `{skipped_pack.pack_key}`: 缺少依赖 {missing_modules}")
    else:
        lines.append("- 无")

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
        "- `option-scaffold focus show`",
        "- `option-scaffold focus refresh`",
        f"- `{smoke_test_command}`",
        f"- `{full_test_command}`",
        "",
        "## Test Modes",
        "",
        "- `smoke`：默认排除名称包含 `property` / `pbt` 的测试节点。",
        "- `full`：运行当前焦点的完整 runnable selectors。",
        "",
        "## Current Strategy Commands",
        "",
        *[f"- `{item}`" for item in commands],
    ]
    return "\n".join(lines) + "\n"
