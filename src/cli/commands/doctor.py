from __future__ import annotations

from importlib.util import find_spec
from pathlib import Path
import sys

import typer

from src import __version__
from src.cli.common import (
    CheckResult,
    EXIT_CODE_FAILURE,
    abort,
    build_artifact,
    build_error,
    display_path,
    echo_check,
    emit_single_json,
    flag_enabled,
    load_project_dotenv,
    resolve_project_path,
)
from src.main.bootstrap.database_factory import DatabaseFactory
from src.main.config.config_loader import ConfigLoader


def _ok(title: str, detail: str) -> CheckResult:
    return CheckResult(status="OK", title=title, detail=detail)


def _warn(title: str, detail: str) -> CheckResult:
    return CheckResult(status="WARN", title=title, detail=detail)


def _error(title: str, detail: str) -> CheckResult:
    return CheckResult(status="ERROR", title=title, detail=detail)


def _module_available(module_name: str) -> bool:
    try:
        return find_spec(module_name) is not None
    except ValueError:
        return False


def _check_required_file(path: Path, title: str) -> CheckResult:
    if path.exists():
        return _ok(title, display_path(path))
    return _error(title, f"缺少 {display_path(path)}")


def collect_doctor_results(*, check_db: bool) -> tuple[list[CheckResult], dict[str, object], list[dict[str, str]], int, int]:
    results: list[CheckResult] = []
    artifacts: list[dict[str, str]] = []

    python_version = ".".join(str(part) for part in sys.version_info[:3])
    if sys.version_info >= (3, 11):
        results.append(_ok("Python", f"{python_version}（满足 >= 3.11）"))
    else:
        results.append(_error("Python", f"{python_version}（需要 >= 3.11）"))

    results.append(_ok("CLI 版本", __version__))

    for title, raw_path in [
        ("项目元数据", "pyproject.toml"),
        ("策略配置", "config/strategy_config.toml"),
        ("交易标的配置", "config/general/trading_target.toml"),
        ("示例目录说明", "example/README.md"),
    ]:
        resolved = resolve_project_path(raw_path)
        results.append(_check_required_file(resolved, title))
        if resolved.exists():
            artifacts.append(build_artifact(resolved))

    env_path = load_project_dotenv()
    if env_path is not None:
        results.append(_ok("环境变量文件", display_path(env_path)))
        artifacts.append(build_artifact(env_path, label=".env"))
    else:
        results.append(_warn("环境变量文件", "未找到 .env，将只读取当前进程环境变量"))

    for title, module_name in [
        ("CLI 依赖 typer", "typer"),
        ("CLI 依赖 python-dotenv", "dotenv"),
        ("运行依赖 vnpy", "vnpy"),
        ("运行依赖 vnpy_portfoliostrategy", "vnpy_portfoliostrategy"),
    ]:
        if _module_available(module_name):
            results.append(_ok(title, "可导入"))
        else:
            results.append(_warn(title, "当前环境中未检测到"))

    missing_db_env = DatabaseFactory.validate_env_vars()
    if missing_db_env:
        results.append(_warn("数据库环境变量", f"缺少 {', '.join(missing_db_env)}"))
    else:
        results.append(_ok("数据库环境变量", "已配置 VnPy 数据库必需项"))

    try:
        gateway_config = ConfigLoader.load_gateway_config()
        ConfigLoader.validate_gateway_config(gateway_config)
        results.append(_ok("CTP 网关环境", "已检测到交易/行情地址与基础凭据"))
    except Exception as exc:
        results.append(_warn("CTP 网关环境", str(exc)))

    if check_db:
        if missing_db_env:
            results.append(_error("数据库连通性", "缺少数据库环境变量，无法执行连通性检查"))
        else:
            factory = DatabaseFactory.get_instance()
            try:
                factory.initialize(eager=True)
                if factory.validate_connection():
                    results.append(_ok("数据库连通性", "SELECT 1 成功"))
                else:
                    results.append(_error("数据库连通性", "连接已初始化，但 SELECT 1 未通过"))
            except Exception as exc:
                results.append(_error("数据库连通性", str(exc)))
            finally:
                factory.reset()

    error_count = sum(1 for result in results if result.status == "ERROR")
    warning_count = sum(1 for result in results if result.status == "WARN")
    summary = {
        "python_version": python_version,
        "error_count": error_count,
        "warning_count": warning_count,
        "check_count": len(results),
        "check_db": check_db,
    }
    return results, summary, artifacts, error_count, warning_count


def command(
    strict: str = typer.Option("", "--strict", flag_value="1", show_default=False, help="将警告也视为失败。"),
    check_db: str = typer.Option("", "--check-db", flag_value="1", show_default=False, help="额外尝试连接数据库并执行 SELECT 1。"),
    json_output: bool = False,
) -> None:
    results, summary, artifacts, error_count, warning_count = collect_doctor_results(
        check_db=flag_enabled(check_db)
    )
    strict_enabled = flag_enabled(strict)
    ok = error_count == 0 and not (strict_enabled and warning_count)
    exit_code = 0 if ok else EXIT_CODE_FAILURE

    if json_output:
        emit_single_json(
            "doctor",
            ok=ok,
            data=summary,
            checks=results,
            artifacts=artifacts,
            errors=() if ok else (build_error("Doctor checks failed", error_type="doctor"),),
            exit_code=exit_code,
        )
        if not ok:
            raise typer.Exit(code=exit_code)
        return

    for result in results:
        echo_check(result)

    if not ok:
        typer.echo(f"诊断未通过：{error_count} 个错误，{warning_count} 个提示。")
        raise typer.Exit(code=EXIT_CODE_FAILURE)

    typer.echo(f"诊断完成：{error_count} 个错误，{warning_count} 个提示。")
