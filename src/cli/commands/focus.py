from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
from io import StringIO

import typer

from src.cli.common import (
    EXIT_CODE_FAILURE,
    EXIT_CODE_VALIDATION,
    abort,
    build_artifact,
    build_error,
    capture_cli_failure_json,
    display_path,
    emit_single_json,
    get_project_root,
)
from src.main.focus.renderer import build_recommended_first_pass
from src.main.focus.service import (
    DEFAULT_PACK_KEYS,
    build_focus_context_payload,
    build_focus_test_matrix,
    describe_focus_health,
    focus_test_command,
    initialize_focus,
    load_focus_context,
    refresh_focus,
    run_focus_tests,
)

FOCUS_COMMAND_HELP = "AI-first 策略焦点工作流，优先为 agent 生成可读、可控、可验收的导航层。"
FOCUS_INIT_HELP = "初始化或覆盖一个策略焦点 Manifest，并立即刷新导航文件。"
FOCUS_REFRESH_HELP = "按当前 Focus Manifest 重新生成 SYSTEM_MAP / ACTIVE_SURFACE / TASK_BRIEF / COMMANDS / TASK_ROUTER / TEST_MATRIX / context.json。"
FOCUS_SHOW_HELP = "打印当前策略焦点的三层代码面、Recommended First Pass 与最小命令集。"
FOCUS_TEST_HELP = "默认运行 smoke 焦点测试；使用 --full 运行完整焦点测试集合。"
FOCUS_PACK_CHOICES = DEFAULT_PACK_KEYS


def _emit_context_result(command_name: str, context, *, json_output: bool, message: str | None = None) -> None:
    payload = build_focus_context_payload(context)
    doc_paths = list(payload["generated_docs"].values())
    artifacts = tuple(build_artifact(path) for path in doc_paths)
    if json_output:
        emit_single_json(command_name, ok=True, data=payload, artifacts=artifacts)
        return

    if message:
        typer.echo(message)
    typer.echo(f"当前焦点: {context.manifest.strategy.name}")
    typer.echo(f"Manifest: {display_path(context.manifest.manifest_path)}")
    typer.echo(f"Pack: {', '.join(pack.key for pack in context.resolved_packs)}")
    typer.echo(f"SYSTEM_MAP: {display_path(context.system_map_path)}")
    typer.echo(f"ACTIVE_SURFACE: {display_path(context.active_surface_path)}")
    typer.echo(f"TASK_BRIEF: {display_path(context.task_brief_path)}")
    typer.echo(f"COMMANDS: {display_path(context.commands_path)}")
    typer.echo(f"TASK_ROUTER: {display_path(context.task_router_path)}")
    typer.echo(f"TEST_MATRIX: {display_path(context.test_matrix_path)}")
    typer.echo(f"context.json: {display_path(context.context_json_path)}")
    for line in describe_focus_health(context):
        typer.echo(line)


def init_command(
    name: str,
    trading_target: str = "option-universe",
    strategy_type: str = "custom",
    run_mode: str = "standalone",
    pack: tuple[str, ...] = (),
    without_pack: tuple[str, ...] = (),
    force: str = "",
    json_output: bool = False,
) -> None:
    try:
        context = initialize_focus(
            get_project_root(),
            name,
            trading_target=trading_target,
            strategy_type=strategy_type,
            run_mode=run_mode,
            include_packs=tuple(pack),
            exclude_packs=tuple(without_pack),
            force=str(force).strip().lower() in {"1", "true", "yes", "on"},
        )
    except (FileExistsError, ValueError) as exc:
        if json_output:
            capture_cli_failure_json("focus.init", str(exc), exit_code=EXIT_CODE_VALIDATION)
        abort(str(exc), exit_code=EXIT_CODE_VALIDATION)

    _emit_context_result("focus.init", context, json_output=json_output, message="已初始化策略焦点。")


def refresh_command(strategy: str | None = None, json_output: bool = False) -> None:
    try:
        context = refresh_focus(get_project_root(), strategy)
    except (FileNotFoundError, ValueError) as exc:
        if json_output:
            capture_cli_failure_json("focus.refresh", str(exc), exit_code=EXIT_CODE_VALIDATION)
        abort(str(exc), exit_code=EXIT_CODE_VALIDATION)

    _emit_context_result("focus.refresh", context, json_output=json_output, message="已刷新策略焦点导航。")


def show_command(strategy: str | None = None, json_output: bool = False) -> None:
    try:
        context = load_focus_context(get_project_root(), strategy)
    except (FileNotFoundError, ValueError) as exc:
        if json_output:
            capture_cli_failure_json("focus.show", str(exc), exit_code=EXIT_CODE_VALIDATION)
        abort(str(exc), exit_code=EXIT_CODE_VALIDATION)

    payload = build_focus_context_payload(context)
    recommended_pack, first_entry = build_recommended_first_pass(context)
    payload["recommended_first_pass"] = {
        "pack": recommended_pack,
        "entry": first_entry,
        "smoke_command": focus_test_command(),
        "full_command": focus_test_command(full=True),
    }
    if json_output:
        artifacts = tuple(build_artifact(path) for path in payload["generated_docs"].values())
        emit_single_json("focus.show", ok=True, data=payload, artifacts=artifacts)
        return

    typer.echo(f"策略: {context.manifest.strategy.name}")
    typer.echo(f"Manifest: {display_path(context.manifest.manifest_path)}")
    typer.echo(f"Pack: {', '.join(pack.key for pack in context.resolved_packs)}")
    typer.echo("")
    typer.echo("Recommended First Pass:")
    typer.echo(f"- pack: {recommended_pack}")
    typer.echo(f"- first entry: {display_path(first_entry)}")
    typer.echo(f"- smoke: {focus_test_command()}")
    typer.echo(f"- full: {focus_test_command(full=True)}")
    typer.echo(f"- docs: {display_path(context.task_router_path)}, {display_path(context.test_matrix_path)}")
    typer.echo("")
    typer.echo("Focus Health:")
    for line in describe_focus_health(context):
        typer.echo(f"- {line}")
    typer.echo("")
    typer.echo("Editable Surface:")
    for path in context.manifest.editable_paths:
        typer.echo(f"- {path}")
    typer.echo("")
    typer.echo("Support Surface:")
    for path in context.manifest.reference_paths:
        typer.echo(f"- {path}")
    typer.echo("")
    typer.echo("Frozen Surface:")
    for path in context.manifest.frozen_paths:
        typer.echo(f"- {path}")


def test_command(
    strategy: str | None = None,
    extra_args: tuple[str, ...] = (),
    *,
    full: bool = False,
    json_output: bool = False,
) -> None:
    try:
        context = load_focus_context(get_project_root(), strategy)
        test_matrix = build_focus_test_matrix(context)
        selectors = test_matrix.full_selectors if full else test_matrix.smoke_selectors
        skipped_packs = [
            {
                "pack_key": item.pack_key,
                "missing_modules": list(item.missing_modules),
            }
            for item in test_matrix.skipped_packs
        ]

        if json_output:
            captured_stdout = StringIO()
            captured_stderr = StringIO()
            with redirect_stdout(captured_stdout), redirect_stderr(captured_stderr):
                exit_code = run_focus_tests(get_project_root(), strategy, extra_args, full=full)
            emit_single_json(
                "focus.test",
                ok=exit_code == 0,
                data={
                    "mode": "full" if full else "smoke",
                    "selectors": list(selectors),
                    "skipped_packs": skipped_packs,
                    "captured_stdout": captured_stdout.getvalue(),
                    "captured_stderr": captured_stderr.getvalue(),
                },
                errors=() if exit_code == 0 else (build_error("Focus tests failed", error_type="pytest"),),
                exit_code=exit_code,
            )
            if exit_code:
                raise typer.Exit(code=exit_code)
            return

        typer.echo(f"测试模式: {'full' if full else 'smoke'}")
        if full:
            typer.echo("节点过滤: 无（运行完整焦点测试集合）")
        else:
            typer.echo("节点过滤:")
            for description in test_matrix.smoke_filter_descriptions:
                typer.echo(f"- {description}")
        typer.echo(f"将运行 {len(selectors)} 个焦点测试选择器。")
        for selector in selectors:
            typer.echo(f"- {selector}")
        for item in skipped_packs:
            typer.echo(
                f"- 跳过 `{item['pack_key']}` pack 测试：缺少依赖 {', '.join(item['missing_modules'])}",
                err=True,
            )
        exit_code = run_focus_tests(get_project_root(), strategy, extra_args, full=full)
    except ModuleNotFoundError as exc:
        if json_output:
            capture_cli_failure_json("focus.test", str(exc), exit_code=EXIT_CODE_FAILURE)
        abort(str(exc), exit_code=EXIT_CODE_FAILURE)
    except (FileNotFoundError, ValueError) as exc:
        if json_output:
            capture_cli_failure_json("focus.test", str(exc), exit_code=EXIT_CODE_VALIDATION)
        abort(str(exc), exit_code=EXIT_CODE_VALIDATION)

    if exit_code:
        raise typer.Exit(code=exit_code)
