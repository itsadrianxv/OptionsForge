from __future__ import annotations

from pathlib import Path

import pytest

import src.main.focus.service as focus_service_module
from src.cli.common import render_cli_command
from src.main.focus.service import (
    build_focus_test_matrix,
    initialize_focus,
    load_focus_context,
    refresh_focus,
    run_focus_tests,
)
from tests.focus_testkit import build_fake_focus_repo, write_current_manifest


def test_initialize_focus_writes_manifest_pointer_and_navigation(tmp_path: Path) -> None:
    repo_root = build_fake_focus_repo(tmp_path)

    context = initialize_focus(
        repo_root,
        "alpha",
        trading_target="510050",
        strategy_type="volatility",
        run_mode="paper",
    )

    assert context.manifest.manifest_path.exists()
    assert (repo_root / ".focus" / "current.toml").exists()
    assert (repo_root / ".focus" / "SYSTEM_MAP.md").exists()
    assert (repo_root / ".focus" / "ACTIVE_SURFACE.md").exists()
    assert (repo_root / ".focus" / "TASK_BRIEF.md").exists()
    assert (repo_root / ".focus" / "COMMANDS.md").exists()
    assert (repo_root / ".focus" / "TASK_ROUTER.md").exists()
    assert (repo_root / ".focus" / "TEST_MATRIX.md").exists()
    assert "alpha" in (repo_root / ".focus" / "SYSTEM_MAP.md").read_text(encoding="utf-8")
    assert render_cli_command("focus test --full") in (repo_root / ".focus" / "COMMANDS.md").read_text(
        encoding="utf-8"
    )
    assert "### `selection`" in (repo_root / ".focus" / "TASK_ROUTER.md").read_text(encoding="utf-8")
    assert "## Smoke" in (repo_root / ".focus" / "TEST_MATRIX.md").read_text(encoding="utf-8")
    assert "## Full" in (repo_root / ".focus" / "TEST_MATRIX.md").read_text(encoding="utf-8")


def test_load_focus_context_rejects_unknown_pack(tmp_path: Path) -> None:
    repo_root = build_fake_focus_repo(tmp_path)
    write_current_manifest(
        repo_root,
        "alpha",
        """
packs = ["kernel", "unknown-pack"]
editable_paths = ["src/strategy/strategy_entry.py"]
reference_paths = ["src/main"]
frozen_paths = [".git"]

[strategy]
name = "alpha"
trading_target = "510050"
strategy_type = "custom"
run_mode = "standalone"
summary = "demo"

[cli]
primary = "python -m src.cli.app"
installed_alias = "option-scaffold"
cwd = "repo-root"

[entrypoints]
run = "python -m src.cli.app run --config config/strategy_config.toml --paper"
backtest = "python -m src.cli.app backtest --config config/strategy_config.toml --start 2025-01-01 --end 2025-03-01 --no-chart"
validate = "python -m src.cli.app validate --config config/strategy_config.toml"
monitor = "python src/web/app.py"

[acceptance]
summary = "demo"
completion_checks = ["ok"]
minimal_test_command = "python -m src.cli.app focus test"
test_selectors = ["tests/main/focus"]
key_logs = ["校验通过"]
key_outputs = [".focus/SYSTEM_MAP.md"]
""".strip()
        + "\n",
    )

    with pytest.raises(ValueError, match="未知 pack"):
        load_focus_context(repo_root)


def test_load_focus_context_rejects_editable_frozen_overlap(tmp_path: Path) -> None:
    repo_root = build_fake_focus_repo(tmp_path)
    write_current_manifest(
        repo_root,
        "alpha",
        """
packs = ["kernel"]
editable_paths = ["src/strategy/strategy_entry.py", ".git"]
reference_paths = ["src/main"]
frozen_paths = [".git"]

[strategy]
name = "alpha"
trading_target = "510050"
strategy_type = "custom"
run_mode = "standalone"
summary = "demo"

[cli]
primary = "python -m src.cli.app"
installed_alias = "option-scaffold"
cwd = "repo-root"

[entrypoints]
run = "python -m src.cli.app run --config config/strategy_config.toml --paper"
backtest = "python -m src.cli.app backtest --config config/strategy_config.toml --start 2025-01-01 --end 2025-03-01 --no-chart"
validate = "python -m src.cli.app validate --config config/strategy_config.toml"
monitor = "python src/web/app.py"

[acceptance]
summary = "demo"
completion_checks = ["ok"]
minimal_test_command = "python -m src.cli.app focus test"
test_selectors = ["tests/main/focus"]
key_logs = ["校验通过"]
key_outputs = [".focus/SYSTEM_MAP.md"]
""".strip()
        + "\n",
    )

    with pytest.raises(ValueError, match="editable_paths"):
        load_focus_context(repo_root)


def test_load_focus_context_rejects_missing_paths_and_commands(tmp_path: Path) -> None:
    repo_root = build_fake_focus_repo(tmp_path)
    write_current_manifest(
        repo_root,
        "alpha",
        """
packs = ["kernel"]
editable_paths = ["src/strategy/strategy_entry.py"]
reference_paths = ["missing/path.py"]
frozen_paths = [".git"]

[strategy]
name = "alpha"
trading_target = "510050"
strategy_type = "custom"
run_mode = "standalone"
summary = "demo"

[cli]
primary = "python -m src.cli.app"
installed_alias = "option-scaffold"
cwd = "repo-root"

[entrypoints]
run = "python -m src.cli.app run --config config/strategy_config.toml --paper"
backtest = "python -m src.cli.app backtest --config config/strategy_config.toml --start 2025-01-01 --end 2025-03-01 --no-chart"
validate = "python -m src.cli.app validate --config config/strategy_config.toml"
monitor = ""

[acceptance]
summary = "demo"
completion_checks = ["ok"]
minimal_test_command = "python -m src.cli.app focus test"
test_selectors = ["tests/main/focus"]
key_logs = ["校验通过"]
key_outputs = [".focus/SYSTEM_MAP.md"]
""".strip()
        + "\n",
    )

    with pytest.raises(ValueError, match="entrypoints.monitor"):
        load_focus_context(repo_root)


def test_load_focus_context_rejects_pack_cycle(tmp_path: Path) -> None:
    repo_root = build_fake_focus_repo(tmp_path)
    cycle_pack = repo_root / "focus" / "packs" / "kernel" / "pack.toml"
    cycle_pack.write_text(
        """
key = "kernel"
depends_on = ["backtest"]
owned_paths = ["src/strategy/strategy_entry.py"]
config_keys = ["strategies"]
test_selectors = ["tests/cli/test_app.py"]
cli_commands = ["validate --config config/strategy_config.toml"]
shell_commands = []
agent_notes = ["cycle"]
""".strip()
        + "\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="依赖循环"):
        initialize_focus(
            repo_root,
            "alpha",
            trading_target="510050",
            strategy_type="custom",
            run_mode="standalone",
        )


def test_build_focus_test_matrix_skips_missing_dependency_packs(tmp_path: Path, monkeypatch) -> None:
    repo_root = build_fake_focus_repo(tmp_path)
    context = initialize_focus(
        repo_root,
        "alpha",
        trading_target="510050",
        strategy_type="volatility",
        run_mode="paper",
    )

    monkeypatch.setattr(
        focus_service_module,
        "_module_available",
        lambda module_name: module_name != "chinese_calendar",
    )

    matrix = build_focus_test_matrix(context)

    assert "tests/main/focus" in matrix.full_selectors
    assert matrix.smoke_keyword_expression == "not property and not pbt"
    assert any(item.pack_key == "backtest" for item in matrix.skipped_packs)


def test_focus_context_payload_includes_cli_metadata(tmp_path: Path) -> None:
    repo_root = build_fake_focus_repo(tmp_path)
    context = initialize_focus(
        repo_root,
        "alpha",
        trading_target="510050",
        strategy_type="volatility",
        run_mode="paper",
    )

    payload = focus_service_module.build_focus_context_payload(context)

    assert payload["cli"] == {
        "primary": "python -m src.cli.app",
        "installed_alias": "option-scaffold",
        "cwd": "repo-root",
    }


def test_pack_command_schema_renders_cli_and_shell_commands(tmp_path: Path) -> None:
    repo_root = build_fake_focus_repo(tmp_path)
    context = initialize_focus(
        repo_root,
        "alpha",
        trading_target="510050",
        strategy_type="volatility",
        run_mode="paper",
    )
    packs_by_key = {pack.key: pack for pack in context.resolved_packs}

    assert packs_by_key["kernel"].commands == (
        render_cli_command("validate --config config/strategy_config.toml"),
        render_cli_command("run --config config/strategy_config.toml --paper"),
    )
    assert packs_by_key["web"].commands == ("python src/web/app.py",)
    assert packs_by_key["deploy"].commands == (
        "docker compose --env-file deploy/.env -f deploy/docker-compose.yml up -d --build",
    )


def test_run_focus_tests_defaults_to_smoke_filter(tmp_path: Path, monkeypatch) -> None:
    repo_root = build_fake_focus_repo(tmp_path)
    initialize_focus(
        repo_root,
        "alpha",
        trading_target="510050",
        strategy_type="volatility",
        run_mode="paper",
    )

    captured: dict[str, list[str]] = {}

    def fake_pytest_main(args: list[str]) -> int:
        captured["args"] = args
        return 0

    monkeypatch.setattr(pytest, "main", fake_pytest_main)
    monkeypatch.setattr(
        focus_service_module,
        "_module_available",
        lambda _module_name: True,
    )

    exit_code = run_focus_tests(repo_root)

    assert exit_code == 0
    assert "-k" in captured["args"]
    keyword_expression = captured["args"][captured["args"].index("-k") + 1]
    assert "not property" in keyword_expression
    assert "not pbt" in keyword_expression


def test_run_focus_tests_merges_user_keyword_filter_in_smoke_mode(tmp_path: Path, monkeypatch) -> None:
    repo_root = build_fake_focus_repo(tmp_path)
    initialize_focus(
        repo_root,
        "alpha",
        trading_target="510050",
        strategy_type="volatility",
        run_mode="paper",
    )

    captured: dict[str, list[str]] = {}

    def fake_pytest_main(args: list[str]) -> int:
        captured["args"] = args
        return 0

    monkeypatch.setattr(pytest, "main", fake_pytest_main)
    monkeypatch.setattr(
        focus_service_module,
        "_module_available",
        lambda _module_name: True,
    )

    exit_code = run_focus_tests(repo_root, extra_args=("-k", "delta"))

    assert exit_code == 0
    keyword_expression = captured["args"][captured["args"].index("-k") + 1]
    assert "(delta)" in keyword_expression
    assert "not property" in keyword_expression
    assert "not pbt" in keyword_expression


def test_run_focus_tests_full_mode_omits_smoke_filter(tmp_path: Path, monkeypatch) -> None:
    repo_root = build_fake_focus_repo(tmp_path)
    initialize_focus(
        repo_root,
        "alpha",
        trading_target="510050",
        strategy_type="volatility",
        run_mode="paper",
    )

    captured: dict[str, list[str]] = {}

    def fake_pytest_main(args: list[str]) -> int:
        captured["args"] = args
        return 0

    monkeypatch.setattr(pytest, "main", fake_pytest_main)
    monkeypatch.setattr(
        focus_service_module,
        "_module_available",
        lambda _module_name: True,
    )

    exit_code = run_focus_tests(repo_root, full=True)

    assert exit_code == 0
    assert "-k" not in captured["args"]


def test_refresh_focus_regenerates_router_and_matrix(tmp_path: Path, monkeypatch) -> None:
    repo_root = build_fake_focus_repo(tmp_path)
    initialize_focus(
        repo_root,
        "alpha",
        trading_target="510050",
        strategy_type="volatility",
        run_mode="paper",
    )

    monkeypatch.setattr(
        focus_service_module,
        "_module_available",
        lambda module_name: module_name != "chinese_calendar",
    )

    refresh_focus(repo_root)

    task_router = (repo_root / ".focus" / "TASK_ROUTER.md").read_text(encoding="utf-8")
    test_matrix = (repo_root / ".focus" / "TEST_MATRIX.md").read_text(encoding="utf-8")

    assert "Task type" in task_router
    assert "Smoke" in test_matrix
    assert "Skipped Packs" in test_matrix
