from __future__ import annotations

from pathlib import Path

import typer

from src.cli.common import (
    EXIT_CODE_FAILURE,
    EXIT_CODE_VALIDATION,
    NdjsonEmitter,
    abort,
    append_flag,
    append_option,
    build_artifact,
    build_error,
    capture_cli_failure_json,
    flag_enabled,
    invoke_legacy_main,
    utc_now_iso,
    write_command_artifact,
)


def _build_argv(
    *,
    config: Path | None,
    start: str | None,
    end: str | None,
    capital: int | None,
    rate: float | None,
    slippage: float | None,
    size: int | None,
    pricetick: float | None,
    no_chart: str,
) -> list[str]:
    argv: list[str] = []
    append_option(argv, "--config", config)
    append_option(argv, "--start", start)
    append_option(argv, "--end", end)
    append_option(argv, "--capital", capital)
    append_option(argv, "--rate", rate)
    append_option(argv, "--slippage", slippage)
    append_option(argv, "--size", size)
    append_option(argv, "--pricetick", pricetick)
    append_flag(argv, "--no-chart", flag_enabled(no_chart))
    return argv


def command(
    config: Path | None = typer.Option(None, "--config", help="策略配置文件路径。"),
    start: str | None = typer.Option(None, "--start", help="开始日期，格式 YYYY-MM-DD。"),
    end: str | None = typer.Option(None, "--end", help="结束日期，格式 YYYY-MM-DD。"),
    capital: int | None = typer.Option(None, "--capital", help="初始资金。"),
    rate: float | None = typer.Option(None, "--rate", help="手续费率。"),
    slippage: float | None = typer.Option(None, "--slippage", help="滑点。"),
    size: int | None = typer.Option(None, "--size", help="合约乘数。"),
    pricetick: float | None = typer.Option(None, "--pricetick", help="最小价格变动。"),
    no_chart: str = typer.Option("", "--no-chart", flag_value="1", show_default=False, help="不显示图表。"),
    json_output: bool = False,
) -> None:
    argv = _build_argv(
        config=config,
        start=start,
        end=end,
        capital=capital,
        rate=rate,
        slippage=slippage,
        size=size,
        pricetick=pricetick,
        no_chart=no_chart,
    )

    if not json_output:
        try:
            from src.backtesting.cli import main as legacy_main

            exit_code = invoke_legacy_main(legacy_main, argv)
        except ModuleNotFoundError as exc:
            abort(
                f"回测命令缺少依赖: {exc.name}。请先执行 `pip install -r requirements.txt`，然后运行 `pip install -e .`。",
                exit_code=EXIT_CODE_FAILURE,
            )
        except FileNotFoundError as exc:
            missing_path = exc.filename or str(exc)
            abort(f"回测命令找不到文件: {missing_path}")
        except ValueError as exc:
            abort(str(exc))
        except Exception as exc:
            abort(f"回测命令执行失败: {exc}", exit_code=EXIT_CODE_FAILURE)

        if exit_code:
            raise typer.Exit(code=exit_code)
        return

    emitter = NdjsonEmitter("backtest")
    started_at = utc_now_iso()
    inputs = {
        "config": str(config) if config else None,
        "start": start,
        "end": end,
        "capital": capital,
        "rate": rate,
        "slippage": slippage,
        "size": size,
        "pricetick": pricetick,
        "no_chart": flag_enabled(no_chart),
    }
    emitter.start(**inputs)
    emitter.phase(name="parse", status="start")

    try:
        from src.backtesting.cli import execute, parse_args

        args = parse_args(argv)
        emitter.phase(name="parse", status="complete")
        emitter.phase(name="execute", status="start")
        summary = execute(args)
        emitter.phase(name="execute", status="complete", ok=bool(summary.get("ok", True)))
        finished_at = utc_now_iso()
        errors = () if summary.get("ok", True) else (build_error("Backtest finished without a successful result", error_type="backtest"),)
        artifact_path = write_command_artifact(
            "backtest",
            ok=bool(summary.get("ok", True)),
            command="backtest",
            started_at=started_at,
            finished_at=finished_at,
            inputs=inputs,
            summary=summary,
            errors=errors,
        )
        emitter.artifact(path=artifact_path, label="backtest-latest-json")
        emitter.result(ok=bool(summary.get("ok", True)), exit_code=0 if summary.get("ok", True) else EXIT_CODE_FAILURE, summary=summary)
        if not summary.get("ok", True):
            raise typer.Exit(code=EXIT_CODE_FAILURE)
    except ModuleNotFoundError as exc:
        emitter.error(message=f"Missing dependency: {exc.name}", error_type="module_not_found")
        emitter.result(ok=False, exit_code=EXIT_CODE_FAILURE)
        raise typer.Exit(code=EXIT_CODE_FAILURE)
    except FileNotFoundError as exc:
        emitter.error(message=exc.filename or str(exc), error_type="file_not_found")
        emitter.result(ok=False, exit_code=EXIT_CODE_VALIDATION)
        raise typer.Exit(code=EXIT_CODE_VALIDATION)
    except ValueError as exc:
        emitter.error(message=str(exc), error_type="validation")
        emitter.result(ok=False, exit_code=EXIT_CODE_VALIDATION)
        raise typer.Exit(code=EXIT_CODE_VALIDATION)
    except typer.Exit:
        raise
    except Exception as exc:
        emitter.error(message=str(exc), error_type="exception")
        emitter.result(ok=False, exit_code=EXIT_CODE_FAILURE)
        raise typer.Exit(code=EXIT_CODE_FAILURE)
