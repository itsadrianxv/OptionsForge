from __future__ import annotations

from pathlib import Path

import typer

from src.cli.commands.create import (
    CREATE_CLEAR_HELP,
    CREATE_DESTINATION_HELP,
    CREATE_FORCE_HELP,
    CREATE_NO_INTERACTIVE_HELP,
    CREATE_OVERWRITE_HELP,
    CREATE_PRESET_HELP,
    CREATE_SET_HELP,
    CREATE_WITH_HELP,
    CREATE_WITH_OPTION_HELP,
    CREATE_WITHOUT_HELP,
    CREATE_WITHOUT_OPTION_HELP,
)
from src.cli.common import (
    EXIT_CODE_FAILURE,
    EXIT_CODE_VALIDATION,
    NdjsonEmitter,
    abort,
    capture_cli_failure_json,
    flag_enabled,
    get_project_root,
)
from src.main.forge.service import run_forge
from src.main.scaffold.models import CapabilityKey, CapabilityOptionKey, CreateOptions


def _to_capabilities(values: tuple[str, ...]) -> tuple[CapabilityKey, ...]:
    return tuple(CapabilityKey(value) for value in values)


def _to_options(values: tuple[str, ...]) -> tuple[CapabilityOptionKey, ...]:
    return tuple(CapabilityOptionKey(value) for value in values)


def command(
    name: str | None = typer.Argument(None, help="策略名称；若当前目录已有 strategy_spec.toml 可省略。"),
    spec: Path | None = typer.Option(None, "--spec", help="显式指定 strategy_spec.toml 路径。"),
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
    no_interactive: str = typer.Option("", "--no-interactive", flag_value="1", show_default=False, help=CREATE_NO_INTERACTIVE_HELP),
    json_output: bool = False,
) -> None:
    create_options = CreateOptions(
        name=name,
        destination=destination,
        preset=preset,
        include_capabilities=_to_capabilities(with_),
        exclude_capabilities=_to_capabilities(without),
        include_options=_to_options(with_option),
        exclude_options=_to_options(without_option),
        no_interactive=True if not flag_enabled(no_interactive) else True,
        force=flag_enabled(force),
        clear=flag_enabled(clear),
        overwrite=flag_enabled(overwrite),
        config_values=tuple(set_values),
    )

    if json_output:
        emitter = NdjsonEmitter("forge")
        emitter.start(
            name=name,
            spec=str(spec) if spec else None,
            destination=str(destination),
        )
        try:
            result = run_forge(get_project_root(), spec_path=spec, create_options=create_options)
        except ValueError as exc:
            emitter.error(message=str(exc), error_type="validation")
            emitter.result(ok=False, exit_code=EXIT_CODE_VALIDATION)
            raise typer.Exit(code=EXIT_CODE_VALIDATION)
        except FileNotFoundError as exc:
            emitter.error(message=str(exc), error_type="file_not_found")
            emitter.result(ok=False, exit_code=EXIT_CODE_VALIDATION)
            raise typer.Exit(code=EXIT_CODE_VALIDATION)
        except Exception as exc:
            emitter.error(message=str(exc), error_type="exception")
            emitter.result(ok=False, exit_code=EXIT_CODE_FAILURE)
            raise typer.Exit(code=EXIT_CODE_FAILURE)

        for phase in result.phases:
            emitter.emit("phase_start", {"name": phase.name})
            emitter.emit("phase_result", {"name": phase.name, "status": phase.status, "detail": phase.detail})
        for artifact in result.artifacts:
            emitter.artifact(path=artifact["path"], label=artifact.get("label"), kind=artifact.get("kind", "file"))
        ok = result.validate_ok and result.focus_test_ok
        emitter.result(
            ok=ok,
            exit_code=0 if ok else EXIT_CODE_FAILURE,
            workspace_root=str(result.workspace_root),
            spec_path=str(result.spec_path),
            validate_summary=result.validate_summary,
            focus_test_summary=result.focus_test_summary,
        )
        if not ok:
            raise typer.Exit(code=EXIT_CODE_FAILURE)
        return

    try:
        result = run_forge(get_project_root(), spec_path=spec, create_options=create_options)
    except ValueError as exc:
        abort(str(exc), exit_code=EXIT_CODE_VALIDATION)
    except FileNotFoundError as exc:
        abort(str(exc), exit_code=EXIT_CODE_VALIDATION)

    typer.echo(f"Forge workspace: {result.workspace_root}")
    typer.echo(f"Strategy spec: {result.spec_path}")
    typer.echo("Phases:")
    for phase in result.phases:
        typer.echo(f"- {phase.name}: {phase.status} ({phase.detail})")
    typer.echo(f"validate: {result.validate_summary}")
    typer.echo(f"focus test: {result.focus_test_summary}")
    typer.echo("Artifacts:")
    for artifact in result.artifacts:
        typer.echo(f"- {artifact['label']}: {artifact['path']}")

    if not (result.validate_ok and result.focus_test_ok):
        raise typer.Exit(code=EXIT_CODE_FAILURE)
