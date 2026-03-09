"""整仓库脚手架交互式提问层。"""

from __future__ import annotations

import sys

import click

from .catalog import (
    CAPABILITY_ORDER,
    DEFAULT_PRESET_KEY,
    DEFAULT_PROJECT_NAME,
    apply_auto_fix_preview,
    build_enabled_options_auto_fix_preview,
    capability_label,
    capability_option_label,
    derive_capabilities,
    get_capability_options,
    get_preset,
    get_preset_keys,
    resolve_capability_options,
    slugify,
)
from .models import CapabilityKey, CapabilityOptionKey, CreateOptions
from .next_steps import build_next_step_commands


CAPABILITY_PROMPT_DESCRIPTIONS: dict[CapabilityKey, str] = {
    CapabilityKey.SELECTION: "补齐标的筛选、期权链读取与合约挑选的基础流程。",
    CapabilityKey.POSITION_SIZING: "补上仓位 sizing 与头寸规模控制能力。",
    CapabilityKey.PRICING: "提供定价与估值相关能力，便于做理论价校验。",
    CapabilityKey.GREEKS_RISK: "增加 Greeks 计算与组合层面的风险约束。",
    CapabilityKey.EXECUTION: "启用智能下单与高级调度，适合实盘接入前扩展。",
    CapabilityKey.HEDGING: "补充 Delta / Vega 等对冲能力，便于控制组合暴露。",
    CapabilityKey.MONITORING: "生成运行监控与状态上报相关接线。",
    CapabilityKey.OBSERVABILITY: "保留决策日志与关键链路，方便排查和复盘。",
}

DIRECTORY_POLICY_DESCRIPTIONS: dict[str, str] = {
    "abort": "停止生成，保持当前目录内容不变。",
    "clear": "清空目标目录后重新生成，会删除目录中的现有文件。",
    "overwrite": "保留目录结构，仅覆盖本次生成时发生冲突的同名文件。",
}


def _echo_section(title: str) -> None:
    click.echo("")
    click.echo(title)


def _format_capability_options(capability: CapabilityKey) -> str:
    return "、".join(
        capability_option_label(option)
        for option in get_capability_options(capability)
    )


def _format_capability_summary(capabilities: tuple[CapabilityKey, ...]) -> str:
    if not capabilities:
        return "最小骨架（暂不启用附加能力）"
    return "、".join(capability_label(item) for item in capabilities)


def _format_option_summary(options: tuple[CapabilityOptionKey, ...]) -> str:
    if not options:
        return "无"
    return "、".join(capability_option_label(item) for item in options)


def _format_directory_policy_summary(
    *,
    has_non_empty_target: bool,
    clear: bool,
    overwrite: bool,
) -> str:
    if not has_non_empty_target:
        return "新建目录（目标目录为空，可直接生成）"
    if clear:
        return "clear（清空目标目录后重新生成）"
    if overwrite:
        return "overwrite（保留目录结构并覆盖冲突文件）"
    return "abort（检测到目录冲突时终止）"


def _echo_next_steps_summary(project_dir_name: str) -> None:
    click.echo("- 生成后建议执行：")
    for command in build_next_step_commands(project_dir_name):
        click.echo(f"  - {command}")


def _collect_capability_selection(
    default_capabilities: set[CapabilityKey],
    default_option_set: set[CapabilityOptionKey],
) -> tuple[tuple[CapabilityKey, ...], tuple[CapabilityOptionKey, ...]]:
    click.echo("默认开关已按预设带出；你可以按项目需要逐项微调。")
    selected: list[CapabilityKey] = []
    selected_options: list[CapabilityOptionKey] = []
    for capability in CAPABILITY_ORDER:
        default_enabled = capability in default_capabilities
        default_text = "默认开启" if default_enabled else "默认关闭"
        click.echo(
            f"- {capability_label(capability)}：{CAPABILITY_PROMPT_DESCRIPTIONS[capability]}（{default_text}）"
        )
        click.echo(f"  包含：{_format_capability_options(capability)}")
        enabled = click.confirm(
            f"是否启用「{capability_label(capability)}」模块",
            default=default_enabled,
            show_default=True,
        )
        if not enabled:
            continue

        selected.append(capability)
        click.echo("  继续确认这个能力组下要落地的子能力：")
        for option in get_capability_options(capability):
            option_enabled = click.confirm(
                f"是否启用子项「{capability_option_label(option)}」",
                default=option in default_option_set,
                show_default=True,
            )
            if option_enabled:
                selected_options.append(option)

    return tuple(selected), tuple(selected_options)


def _echo_auto_fix_preview(selected_options: tuple[CapabilityOptionKey, ...], fixed_options: tuple[CapabilityOptionKey, ...], preview) -> None:
    _echo_section("自动修复预览")
    click.echo(f"- 问题：{preview.error}")
    if preview.add_options:
        click.echo(f"- 将自动启用：{_format_option_summary(preview.add_options)}")
    if preview.remove_options:
        click.echo(f"- 将自动关闭：{_format_option_summary(preview.remove_options)}")
    click.echo(f"- 修复后子选项：{_format_option_summary(fixed_options)}")
    click.echo(f"- 修复建议：{preview.suggestion}")


def supports_interactive_prompt() -> bool:
    """判断当前终端是否适合交互式提问。"""
    return sys.stdin.isatty() and sys.stdout.isatty()


def should_prompt_for_create(options: CreateOptions) -> bool:
    """判断 create 命令是否应进入交互模式。"""
    if options.no_interactive or options.use_default or not supports_interactive_prompt():
        return False

    if not options.name or not options.preset:
        return True

    has_capability_overrides = bool(
        options.include_capabilities
        or options.exclude_capabilities
        or options.include_options
        or options.exclude_options
    )
    target_root = options.destination / slugify(options.name)
    has_non_empty_target = target_root.exists() and target_root.is_dir() and any(target_root.iterdir())
    return not has_capability_overrides or (has_non_empty_target and not (options.clear or options.overwrite))


def prompt_for_create_options(options: CreateOptions) -> CreateOptions:
    """收集 create 命令所需的交互式选择。"""
    click.echo("欢迎使用 option-scaffold 项目创建向导。")
    click.echo("接下来会依次确认项目名称、策略预设、模块定制方式、目录处理方式与最终确认。")
    click.echo("带默认值的问题可直接回车接受默认配置。")

    _echo_section("第 1 步 · 项目命名")
    name = (options.name or "").strip()
    if not name:
        click.echo("这个名称会同时作为项目目录名、策略包名和默认配置名。")
        name = click.prompt("项目名称", default=DEFAULT_PROJECT_NAME, show_default=True).strip()
    else:
        click.echo(f"已接收项目名称：{name}")

    _echo_section("第 2 步 · 选择策略预设")
    preset_key = (options.preset or "").strip().lower()
    if not preset_key:
        click.echo("可用预设如下：")
        for key in get_preset_keys():
            preset = get_preset(key)
            default_tag = "（默认）" if key == DEFAULT_PRESET_KEY else ""
            click.echo(f"- {key}{default_tag} · {preset.display_name}: {preset.description}")
        preset_key = click.prompt(
            "预设编号",
            type=click.Choice(get_preset_keys(), case_sensitive=False),
            default=DEFAULT_PRESET_KEY,
            show_default=True,
        )
    preset = get_preset(preset_key)
    click.echo(f"已选择预设：{preset.display_name}（{preset.key}）")
    click.echo(f"模板说明：{preset.description}")

    enabled_options = resolve_capability_options(
        preset,
        options.include_capabilities,
        options.exclude_capabilities,
        options.include_options,
        options.exclude_options,
    )
    default_option_tuple = tuple(enabled_options)
    default_option_set = set(default_option_tuple)
    default_capabilities = set(derive_capabilities(default_option_tuple))

    _echo_section("第 3 步 · 是否自定义模块")
    click.echo(f"- 预设默认能力：{_format_capability_summary(derive_capabilities(default_option_tuple))}")
    click.echo(f"- 预设默认子项：{_format_option_summary(default_option_tuple)}")
    customize_modules = click.confirm("是否自定义模块", default=False, show_default=True)

    if customize_modules:
        while True:
            _echo_section("第 4 步 · 自定义能力模块")
            selected_tuple, selected_option_tuple = _collect_capability_selection(
                default_capabilities,
                default_option_set,
            )

            preview = build_enabled_options_auto_fix_preview(
                selected_option_tuple,
                preset_key=preset_key,
            )
            if preview is None:
                break

            fixed_options = apply_auto_fix_preview(selected_option_tuple, preview)
            _echo_auto_fix_preview(selected_option_tuple, fixed_options, preview)
            if click.confirm("是否应用上述自动修复建议", default=True, show_default=True):
                selected_option_tuple = fixed_options
                selected_tuple = derive_capabilities(selected_option_tuple)
                click.echo("已应用自动修复，将使用修复后的能力组合继续生成。")
                break

            retry = click.confirm("是否返回重新选择能力与子选项", default=True, show_default=True)
            if retry:
                default_option_set = set(selected_option_tuple)
                default_capabilities = set(selected_tuple)
                continue

            raise ValueError(f"{preview.error} 建议：{preview.suggestion}")
    else:
        selected_option_tuple = default_option_tuple
        selected_tuple = derive_capabilities(selected_option_tuple)
        click.echo("将直接使用当前预设的默认模块组合，不再逐项询问 capability / option。")

    clear = options.clear
    overwrite = options.overwrite
    target_root = options.destination / slugify(name)
    has_non_empty_target = target_root.exists() and target_root.is_dir() and any(target_root.iterdir())

    _echo_section("第 5 步 · 处理已有目录")
    if has_non_empty_target:
        click.echo(f"检测到目标目录已存在且非空：{target_root}")
        if clear or overwrite:
            policy = "clear" if clear else "overwrite"
            click.echo(f"将沿用已显式指定的目录处理策略：{policy}")
            click.echo(f"- {policy}：{DIRECTORY_POLICY_DESCRIPTIONS[policy]}")
        else:
            click.echo("可选处理策略：")
            for key, description in DIRECTORY_POLICY_DESCRIPTIONS.items():
                click.echo(f"- {key}：{description}")
            policy = click.prompt(
                "目录处理策略",
                type=click.Choice(("abort", "clear", "overwrite"), case_sensitive=False),
                default="abort",
                show_default=True,
            )
            if policy == "abort":
                raise FileExistsError(f"目标目录已存在且非空: {target_root}")
            clear = policy == "clear"
            overwrite = policy == "overwrite"
    else:
        click.echo(f"目标目录可直接创建：{target_root}")

    _echo_section("第 6 步 · 最终确认")
    click.echo(f"- 项目名称：{name}")
    click.echo(f"- 输出目录：{target_root}")
    click.echo(f"- 预设：{preset.display_name}（{preset.key}）")
    click.echo(f"- 启用能力：{_format_capability_summary(selected_tuple)}")
    click.echo(f"- 启用子项：{_format_option_summary(selected_option_tuple)}")
    click.echo(
        f"- 目录处理策略：{_format_directory_policy_summary(has_non_empty_target=has_non_empty_target, clear=clear, overwrite=overwrite)}"
    )
    _echo_next_steps_summary(target_root.name)

    if not click.confirm("确认开始生成项目吗", default=True, show_default=True):
        raise ValueError(f"已取消生成: {target_root}")

    selected_set = set(selected_tuple)
    selected_option_set = set(selected_option_tuple)
    unselected_tuple = tuple(item for item in CAPABILITY_ORDER if item not in selected_set)
    return CreateOptions(
        name=name,
        destination=options.destination,
        preset=preset_key,
        include_capabilities=selected_tuple,
        exclude_capabilities=unselected_tuple,
        include_options=tuple(selected_option_tuple),
        exclude_options=tuple(item for item in CapabilityOptionKey if item not in selected_option_set),
        use_default=False,
        no_interactive=True,
        force=options.force,
        clear=clear,
        overwrite=overwrite,
    )
