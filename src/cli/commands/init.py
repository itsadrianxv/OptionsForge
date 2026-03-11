from __future__ import annotations

from pathlib import Path

import typer

from src.cli.common import (
    EXIT_CODE_VALIDATION,
    abort,
    build_artifact,
    capture_cli_failure_json,
    display_path,
    emit_single_json,
    flag_enabled,
)
from src.main.scaffold.generator import scaffold_strategy


def command(
    name: str = typer.Argument(..., help="策略目录名称，例如 ema_breakout。"),
    destination: Path = typer.Option(Path("example"), "--destination", "-d", help="输出目录，默认写入根目录下的 example/。"),
    force: str = typer.Option("", "--force", flag_value="1", show_default=False, help="目录已存在时允许覆盖文件。"),
    json_output: bool = False,
) -> None:
    try:
        created = scaffold_strategy(name, destination, force=flag_enabled(force))
    except FileExistsError as exc:
        if json_output:
            capture_cli_failure_json("init", str(exc), exit_code=EXIT_CODE_VALIDATION)
        abort(str(exc), exit_code=EXIT_CODE_VALIDATION)

    if json_output:
        emit_single_json(
            "init",
            ok=True,
            data={
                "strategy_name": name,
                "created_path": display_path(created),
            },
            artifacts=(
                build_artifact(created, label="strategy-root", kind="directory"),
                build_artifact(created / "strategy_contract.toml", label="strategy-contract"),
            ),
        )
        return

    typer.echo(f"已生成策略脚手架: {created}")
