from __future__ import annotations

from pathlib import Path

from src.main.scaffold.models import CreateOptions
from src.main.scaffold.project import create_project_scaffold
from src.main.spec.service import (
    create_options_from_spec,
    load_strategy_spec,
    pack_keys_from_spec,
    spec_from_plan,
    write_strategy_spec,
)


def test_strategy_spec_roundtrip_from_scaffold_plan(tmp_path: Path) -> None:
    plan = create_project_scaffold(
        CreateOptions(
            name="alpha_lab",
            destination=tmp_path,
            use_default=True,
        )
    )

    spec = load_strategy_spec(plan.project_root, plan.project_root / "strategy_spec.toml")

    assert spec.strategy.name == "alpha_lab"
    assert spec.scaffold.preset == "custom"
    assert "selection" in [item.value for item in spec.scaffold.capabilities]
    assert "option-selector" in [item.value for item in spec.scaffold.options]
    assert "kernel" in pack_keys_from_spec(spec)


def test_create_options_from_spec_reuses_structured_overrides(tmp_path: Path) -> None:
    plan = create_project_scaffold(
        CreateOptions(
            name="alpha_lab",
            destination=tmp_path,
            use_default=True,
        )
    )
    spec = spec_from_plan(plan)
    spec_path = plan.project_root / "custom_strategy_spec.toml"
    write_strategy_spec(spec, spec_path)
    loaded = load_strategy_spec(plan.project_root, spec_path)

    options = create_options_from_spec(
        loaded,
        destination=tmp_path,
        overwrite=True,
        force=True,
    )

    assert options.name == "alpha_lab"
    assert options.preset == "custom"
    assert options.overwrite is True
    assert options.force is True
