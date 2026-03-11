from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
from dataclasses import dataclass
from io import StringIO
from pathlib import Path

from src.cli.commands.validate import collect_validation_results
from src.cli.common import build_artifact, build_error, utc_now_iso, write_command_artifact
from src.main.focus.service import build_focus_context_payload, initialize_focus, run_focus_tests
from src.main.scaffold.catalog import build_scaffold_plan, slugify
from src.main.scaffold.models import CreateOptions
from src.main.scaffold.project import create_project_scaffold
from src.main.spec.service import (
    build_test_plan_markdown,
    create_options_from_spec,
    default_spec_path,
    load_strategy_spec,
    pack_keys_from_spec,
    spec_from_plan,
    write_strategy_spec,
)


@dataclass(frozen=True)
class ForgePhase:
    name: str
    status: str
    detail: str


@dataclass(frozen=True)
class ForgeResult:
    workspace_root: Path
    spec_path: Path
    phases: tuple[ForgePhase, ...]
    artifacts: tuple[dict[str, str], ...]
    validate_ok: bool
    focus_test_ok: bool
    context_payload: dict[str, object]
    validate_summary: str
    focus_test_summary: str


def _workspace_is_scaffold_root(workspace_root: Path) -> bool:
    return (workspace_root / "pyproject.toml").exists() and (workspace_root / "src").exists()


def _resolve_spec_or_options(
    repo_root: Path,
    *,
    spec_path: Path | None,
    create_options: CreateOptions,
) -> tuple[Path, object, CreateOptions | None, ForgePhase]:
    if spec_path is not None:
        resolved_spec_path = spec_path if spec_path.is_absolute() else repo_root / spec_path
        spec = load_strategy_spec(resolved_spec_path.parent, resolved_spec_path)
        return resolved_spec_path.parent, spec, None, ForgePhase("spec", "loaded", f"Loaded {resolved_spec_path}")

    if create_options.name:
        intended_root = Path(create_options.destination) / slugify(create_options.name)
        intended_spec_path = intended_root / "strategy_spec.toml"
        if intended_spec_path.exists():
            spec = load_strategy_spec(intended_root, intended_spec_path)
            return intended_root, spec, None, ForgePhase("spec", "loaded", f"Loaded {intended_spec_path}")

        plan = build_scaffold_plan(create_options)
        spec = spec_from_plan(plan)
        return plan.project_root, spec, create_options, ForgePhase("spec", "generated", "Synthesized strategy spec from forge options")

    default_path = default_spec_path(repo_root)
    if default_path.exists():
        spec = load_strategy_spec(repo_root, default_path)
        return repo_root, spec, None, ForgePhase("spec", "loaded", f"Loaded {default_path}")

    raise ValueError("No strategy_spec.toml found and no forge name was provided.")


def run_forge(
    repo_root: Path,
    *,
    spec_path: Path | None,
    create_options: CreateOptions,
) -> ForgeResult:
    phases: list[ForgePhase] = []
    artifacts: list[dict[str, str]] = []

    workspace_root, spec, scaffold_options, spec_phase = _resolve_spec_or_options(
        repo_root,
        spec_path=spec_path,
        create_options=create_options,
    )
    phases.append(spec_phase)

    if _workspace_is_scaffold_root(workspace_root):
        write_strategy_spec(spec, workspace_root / "strategy_spec.toml")
        phases.append(ForgePhase("scaffold", "skipped", "Existing workspace detected; scaffold generation skipped"))
    else:
        effective_options = scaffold_options or create_options_from_spec(
            spec,
            destination=workspace_root.parent,
            clear=create_options.clear,
            overwrite=create_options.overwrite,
            force=create_options.force,
        )
        plan = create_project_scaffold(effective_options)
        workspace_root = plan.project_root
        write_strategy_spec(spec, workspace_root / "strategy_spec.toml")
        phases.append(ForgePhase("scaffold", "completed", f"Rendered workspace at {workspace_root}"))

    spec = load_strategy_spec(workspace_root, workspace_root / "strategy_spec.toml")
    artifacts.append(build_artifact(workspace_root / "strategy_spec.toml", label="strategy-spec"))

    context = initialize_focus(
        workspace_root,
        spec.strategy.name,
        trading_target=spec.strategy.trading_target,
        strategy_type=spec.strategy.strategy_type,
        run_mode=spec.strategy.run_mode,
        include_packs=pack_keys_from_spec(spec),
        force=True,
        summary=spec.strategy.summary,
        completion_checks=spec.acceptance.completion_checks,
    )
    context_payload = build_focus_context_payload(context)
    phases.append(ForgePhase("focus", "completed", "Focus manifest and navigation refreshed"))
    artifacts.extend(
        build_artifact(workspace_root / relative_path)
        for relative_path in context_payload["generated_docs"].values()
    )

    test_plan_path = workspace_root / "tests" / "TEST.md"
    test_plan_path.write_text(build_test_plan_markdown(spec), encoding="utf-8")
    phases.append(ForgePhase("test-plan", "completed", f"Rendered {test_plan_path}"))
    artifacts.append(build_artifact(test_plan_path, label="test-plan"))

    started_at = utc_now_iso()
    validate_results, validate_summary_payload, validate_artifacts, error_count, warning_count = collect_validation_results(
        repo_root=workspace_root,
        config=workspace_root / "config" / "strategy_config.toml",
    )
    finished_at = utc_now_iso()
    validate_ok = error_count == 0
    validate_errors = () if validate_ok else (build_error("Validation failed", error_type="validation"),)
    validate_latest = write_command_artifact(
        "validate",
        ok=validate_ok,
        command="validate",
        started_at=started_at,
        finished_at=finished_at,
        inputs={"config": "config/strategy_config.toml"},
        summary=validate_summary_payload,
        artifacts=validate_artifacts,
        errors=validate_errors,
        repo_root=workspace_root,
    )
    validate_summary = f"{'passed' if validate_ok else 'failed'} with {error_count} errors and {warning_count} warnings"
    phases.append(ForgePhase("validate", "completed" if validate_ok else "failed", validate_summary))
    artifacts.extend(validate_artifacts)
    artifacts.append(build_artifact(validate_latest, label="validate-latest-json"))

    captured_stdout = StringIO()
    captured_stderr = StringIO()
    with redirect_stdout(captured_stdout), redirect_stderr(captured_stderr):
        focus_test_exit_code = run_focus_tests(workspace_root)
    focus_test_ok = focus_test_exit_code == 0
    focus_test_summary = f"{'passed' if focus_test_ok else 'failed'} with exit code {focus_test_exit_code}"
    phases.append(ForgePhase("focus-test", "completed" if focus_test_ok else "failed", focus_test_summary))

    test_plan_path.write_text(
        build_test_plan_markdown(
            spec,
            validate_summary=validate_summary,
            focus_test_summary=focus_test_summary,
        ),
        encoding="utf-8",
    )

    if captured_stdout.getvalue().strip():
        artifacts.append(build_artifact(context.test_matrix_path, label="focus-test-matrix"))

    return ForgeResult(
        workspace_root=workspace_root,
        spec_path=workspace_root / "strategy_spec.toml",
        phases=tuple(phases),
        artifacts=tuple(artifacts),
        validate_ok=validate_ok,
        focus_test_ok=focus_test_ok,
        context_payload=context_payload,
        validate_summary=validate_summary,
        focus_test_summary=focus_test_summary,
    )
