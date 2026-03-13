from __future__ import annotations

from pathlib import Path
from typing import Iterable

import typer

from src.cli.common import (
    EXIT_CODE_VALIDATION,
    abort,
    build_artifact,
    capture_cli_failure_json,
    display_path,
    emit_single_json,
    flag_enabled,
    render_cli_command,
)
from src.main.scaffold.models import CapabilityKey, CapabilityOptionKey, CreateOptions, ScaffoldPlan
from src.main.scaffold.next_steps import build_next_step_commands
from src.main.scaffold.project import create_project_scaffold

CREATE_COMMAND_HELP = "创建整仓库级期权策略项目脚手架，支持交互式向导，也支持通过 flags 一次性生成。"
CREATE_COMMAND_EXAMPLES = (
    "常用示例：\n"
    "  交互创建\n"
    f"    {render_cli_command('create alpha_lab')}\n"
    "  默认快速创建\n"
    f"    {render_cli_command('create alpha_lab -y')}\n"
    "  预设模板\n"
    f"    {render_cli_command('create alpha_lab --preset ema-cross -d .\\projects')}\n"
    "  精细能力控制\n"
    f"    {render_cli_command('create alpha_lab --preset custom --with hedging --with-option vega-hedging --no-interactive')}\n"
    "  非交互配置参数\n"
    f"    {render_cli_command('create alpha_lab --preset ema-cross --set setting.max_positions=8 --set signal_kwargs.option_type=put --no-interactive')}"
)
CREATE_NAME_HELP = "项目名称；省略时会进入交互式向导询问。"
CREATE_DESTINATION_HELP = "项目输出父目录；最终会生成到 <destination>/<name>/。"
CREATE_PRESET_HELP = "策略预设；可选 custom、ema-cross、iv-rank、delta-neutral。省略时可在向导中选择。"
CREATE_WITH_HELP = "按能力组显式开启功能，可重复传入；适合非交互模式精确控制。"
CREATE_WITHOUT_HELP = "按能力组显式关闭功能，可重复传入；适合在预设基础上做裁剪。"
CREATE_WITH_OPTION_HELP = "按二级子能力显式开启，可重复传入；用于更细粒度定制。"
CREATE_WITHOUT_OPTION_HELP = "按二级子能力显式关闭，可重复传入；用于更细粒度裁剪。"
CREATE_SET_HELP = "覆盖生成时的配置参数，使用 key=value 形式，可重复传入。"
CREATE_FORCE_HELP = "跳过目录覆盖类操作的二次确认；仅在确认目标目录可被修改时使用。"
CREATE_CLEAR_HELP = "目标目录非空时先清空再生成。"
CREATE_OVERWRITE_HELP = "目标目录非空时保留目录，仅覆盖本次生成的冲突文件。"
CREATE_DEFAULT_HELP = "跳过提问，直接使用默认预设、默认能力和传入的 --set 生成。"
CREATE_NO_INTERACTIVE_HELP = "禁用交互向导，仅按显式 flags 与默认规则执行。"


def _to_capabilities(values: Iterable[str]) -> tuple[CapabilityKey, ...]:
    return tuple(CapabilityKey(value) for value in values)


def _to_options(values: Iterable[str]) -> tuple[CapabilityOptionKey, ...]:
    return tuple(CapabilityOptionKey(value) for value in values)


def _emit_result(plan: ScaffoldPlan, *, json_output: bool) -> None:
    next_steps = build_next_step_commands(plan.project_root.name)
    if json_output:
        emit_single_json(
            "create",
            ok=True,
            data={
                "project_name": plan.project_name,
                "project_root": display_path(plan.project_root),
                "strategy_slug": plan.strategy_slug,
                "preset": plan.preset.key,
                "capabilities": [item.value for item in plan.capabilities],
                "enabled_options": [item.value for item in plan.enabled_options],
                "next_steps": list(next_steps),
            },
            artifacts=(
                build_artifact(plan.project_root, label="project-root", kind="directory"),
                build_artifact(
                    plan.project_root / "config" / "strategy_config.toml",
                    label="strategy-config",
                ),
                build_artifact(
                    plan.project_root / "strategy_spec.toml",
                    label="strategy-spec",
                ),
                build_artifact(
                    plan.project_root / "tests" / "TEST.md",
                    label="test-plan",
                ),
            ),
        )
        return

    typer.echo("项目脚手架已生成完成。")
    typer.echo(f"- 项目根目录：{display_path(plan.project_root)}")
    typer.echo(f"- 策略包：src/strategies/{plan.strategy_slug}")
    typer.echo(f"- 主配置：{display_path(plan.project_root / 'config' / 'strategy_config.toml')}")
    typer.echo(f"- 策略规格：{display_path(plan.project_root / 'strategy_spec.toml')}")
    typer.echo("- 可直接执行的 next steps：")
    for next_command in next_steps:
        typer.echo(f"  - {next_command}")


def command(
    name: str | None = typer.Argument(None, help=CREATE_NAME_HELP),
    destination: Path = typer.Option(Path("."), "--destination", "-d", help=CREATE_DESTINATION_HELP),
    preset: str | None = typer.Option(None, "--preset", help=CREATE_PRESET_HELP),
    with_: tuple[str, ...] = typer.Option((), "--with", help=CREATE_WITH_HELP),
    without: tuple[str, ...] = typer.Option((), "--without", help=CREATE_WITHOUT_HELP),
    with_option: tuple[str, ...] = typer.Option((), "--with-option", help=CREATE_WITH_OPTION_HELP),
    without_option: tuple[str, ...] = typer.Option((), "--without-option", help=CREATE_WITHOUT_OPTION_HELP),
    set_values: tuple[str, ...] = typer.Option((), "--set", help=CREATE_SET_HELP),
    force: str = typer.Option("", "--force", flag_value="1", show_default=False, help=CREATE_FORCE_HELP),
    clear: str = typer.Option("", "--clear", flag_value="1", show_default=False, help=CREATE_CLEAR_HELP),
    overwrite: str = typer.Option("", "--overwrite", flag_value="1", show_default=False, help=CREATE_OVERWRITE_HELP),
    use_default: str = typer.Option("", "-y", "--default", flag_value="1", show_default=False, help=CREATE_DEFAULT_HELP),
    no_interactive: str = typer.Option("", "--no-interactive", flag_value="1", show_default=False, help=CREATE_NO_INTERACTIVE_HELP),
    json_output: bool = False,
) -> None:
    try:
        plan = create_project_scaffold(
            CreateOptions(
                name=name,
                destination=destination,
                preset=preset,
                include_capabilities=_to_capabilities(with_),
                exclude_capabilities=_to_capabilities(without),
                include_options=_to_options(with_option),
                exclude_options=_to_options(without_option),
                use_default=flag_enabled(use_default),
                no_interactive=flag_enabled(no_interactive),
                force=flag_enabled(force),
                clear=flag_enabled(clear),
                overwrite=flag_enabled(overwrite),
                config_values=tuple(set_values),
            )
        )
    except (FileExistsError, ValueError) as exc:
        if json_output:
            capture_cli_failure_json("create", str(exc), exit_code=EXIT_CODE_VALIDATION)
        abort(str(exc), exit_code=EXIT_CODE_VALIDATION)

    _emit_result(plan, json_output=json_output)
