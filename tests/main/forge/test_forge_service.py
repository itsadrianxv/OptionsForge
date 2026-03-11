from __future__ import annotations

from pathlib import Path

from src.cli.common import get_project_root
from src.main.forge.service import run_forge
from src.main.scaffold.models import CreateOptions


def test_run_forge_creates_new_workspace_assets(tmp_path: Path) -> None:
    result = run_forge(
        get_project_root(),
        spec_path=None,
        create_options=CreateOptions(
            name="forge_lab",
            destination=tmp_path,
            use_default=True,
        ),
    )

    workspace_root = tmp_path / "forge_lab"

    assert result.workspace_root == workspace_root
    assert (workspace_root / "strategy_spec.toml").exists()
    assert (workspace_root / ".focus" / "context.json").exists()
    assert (workspace_root / "tests" / "TEST.md").exists()
    assert (workspace_root / "artifacts" / "validate" / "latest.json").exists()
    assert any(phase.name == "focus" for phase in result.phases)


def test_run_forge_rerun_uses_existing_spec_without_creating_nested_workspace(tmp_path: Path) -> None:
    first = run_forge(
        get_project_root(),
        spec_path=None,
        create_options=CreateOptions(
            name="forge_lab",
            destination=tmp_path,
            use_default=True,
        ),
    )

    second = run_forge(
        first.workspace_root,
        spec_path=None,
        create_options=CreateOptions(
            name=None,
            destination=first.workspace_root,
            no_interactive=True,
        ),
    )

    assert second.workspace_root == first.workspace_root
    assert not (first.workspace_root / "forge_lab").exists()
    assert any(phase.name == "scaffold" and phase.status == "skipped" for phase in second.phases)
