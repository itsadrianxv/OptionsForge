from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from src.cli.app import app
from tests.focus_testkit import build_fake_focus_repo

runner = CliRunner()


def _patch_repo_root(monkeypatch, repo_root: Path) -> None:
    monkeypatch.setattr("src.cli.commands.focus.get_project_root", lambda: repo_root)
    monkeypatch.setattr("src.cli.common.get_project_root", lambda: repo_root)


def test_focus_help_lists_subcommands() -> None:
    result = runner.invoke(app, ["focus", "--help"])

    assert result.exit_code == 0
    assert "init" in result.stdout
    assert "refresh" in result.stdout
    assert "show" in result.stdout
    assert "test" in result.stdout


def test_focus_init_creates_manifest_and_navigation(tmp_path: Path, monkeypatch) -> None:
    repo_root = build_fake_focus_repo(tmp_path)
    _patch_repo_root(monkeypatch, repo_root)

    result = runner.invoke(app, ["focus", "init", "alpha"])

    assert result.exit_code == 0
    assert "已初始化策略焦点" in result.stdout
    assert (repo_root / "focus" / "strategies" / "alpha" / "strategy.manifest.toml").exists()
    assert (repo_root / ".focus" / "SYSTEM_MAP.md").exists()


def test_focus_show_uses_current_pointer(tmp_path: Path, monkeypatch) -> None:
    repo_root = build_fake_focus_repo(tmp_path)
    _patch_repo_root(monkeypatch, repo_root)
    runner.invoke(app, ["focus", "init", "alpha"])

    result = runner.invoke(app, ["focus", "show"])

    assert result.exit_code == 0
    assert "Editable Surface" in result.stdout
    assert "config/strategy_config.toml" in result.stdout


def test_focus_test_runs_aggregated_selectors(tmp_path: Path, monkeypatch) -> None:
    repo_root = build_fake_focus_repo(tmp_path)
    _patch_repo_root(monkeypatch, repo_root)
    runner.invoke(app, ["focus", "init", "alpha"])

    captured: list[str] = []

    def fake_main(args: list[str]) -> int:
        captured.extend(args)
        return 0

    monkeypatch.setattr(pytest, "main", fake_main)

    result = runner.invoke(app, ["focus", "test", "--", "-q"])

    assert result.exit_code == 0
    assert "tests/main/focus" in "\n".join(captured)
    assert "-q" in captured
