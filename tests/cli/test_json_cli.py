from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from src.cli.app import app
from src.main.focus.service import initialize_focus
from tests.focus_testkit import build_fake_focus_repo

runner = CliRunner()


def _patch_repo_root(monkeypatch, repo_root: Path) -> None:
    monkeypatch.setattr("src.cli.commands.focus.get_project_root", lambda: repo_root)
    monkeypatch.setattr("src.cli.common.get_project_root", lambda: repo_root)


def test_validate_json_envelope_contains_artifact(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr("src.cli.common.get_project_root", lambda: Path.cwd())
    result = runner.invoke(app, ["validate", "--json"])

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert payload["command"] == "validate"
    assert any(item["label"] == "validate-latest-json" for item in payload["artifacts"])


def test_examples_json_lists_examples() -> None:
    result = runner.invoke(app, ["examples", "--json"])

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert "examples" in payload["data"]


def test_focus_show_json_matches_context_payload(tmp_path: Path, monkeypatch) -> None:
    repo_root = build_fake_focus_repo(tmp_path)
    initialize_focus(
        repo_root,
        "alpha",
        trading_target="510050",
        strategy_type="volatility",
        run_mode="paper",
    )
    _patch_repo_root(monkeypatch, repo_root)

    result = runner.invoke(app, ["focus", "show", "--json"])

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert payload["data"]["strategy"]["name"] == "alpha"
    assert payload["data"]["generated_docs"]["context_json"] == ".focus/context.json"


def test_run_json_outputs_ndjson(monkeypatch) -> None:
    monkeypatch.setattr("src.main.main.main", lambda argv=None: 0)

    result = runner.invoke(app, ["run", "--json"])

    assert result.exit_code == 0
    events = [json.loads(line) for line in result.stdout.splitlines() if line.strip()]
    assert events[0]["event"] == "start"
    assert any(event["event"] == "phase" for event in events)
    assert events[-1]["event"] == "result"


def test_backtest_json_outputs_ndjson_and_writes_artifact(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr("src.cli.common.get_project_root", lambda: tmp_path)
    monkeypatch.setattr("src.backtesting.cli.parse_args", lambda argv=None: object())
    monkeypatch.setattr(
        "src.backtesting.cli.execute",
        lambda args: {
            "ok": True,
            "config_path": "config/strategy_config.toml",
            "statistics": {"total_return": 0.1},
        },
    )

    result = runner.invoke(app, ["backtest", "--json"])

    assert result.exit_code == 0
    events = [json.loads(line) for line in result.stdout.splitlines() if line.strip()]
    assert events[0]["event"] == "start"
    assert any(event["event"] == "artifact" for event in events)
    assert events[-1]["event"] == "result"
    assert (tmp_path / "artifacts" / "backtest" / "latest.json").exists()


def test_forge_json_outputs_phase_events(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr("src.cli.common.get_project_root", lambda: tmp_path)
    spec_path = tmp_path / "strategy_spec.toml"
    spec_path.write_text(
        """
[strategy]
name = "alpha"
summary = "alpha strategy"
trading_target = "510050"
strategy_type = "custom"
run_mode = "standalone"

[scaffold]
preset = "custom"
capabilities = ["selection"]
options = ["future-selection", "option-chain", "option-selector"]

[logic]
entry_rules = ["entry"]
exit_rules = ["exit"]
selection_rules = ["selection"]
sizing_rules = ["sizing"]
risk_rules = ["risk"]
hedging_rules = ["hedging"]
observability_notes = ["obs"]

[acceptance]
completion_checks = ["check"]
focus_packs = ["kernel"]
test_scenarios = ["scenario"]
""".strip()
        + "\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(
        "src.cli.commands.forge.run_forge",
        lambda repo_root, spec_path=None, create_options=None: __import__("types").SimpleNamespace(
            workspace_root=tmp_path,
            spec_path=spec_path or (tmp_path / "strategy_spec.toml"),
            phases=(
                __import__("types").SimpleNamespace(name="spec", status="loaded", detail="loaded"),
                __import__("types").SimpleNamespace(name="focus", status="completed", detail="focus"),
            ),
            artifacts=({"path": "strategy_spec.toml", "label": "strategy-spec", "kind": "file"},),
            validate_ok=True,
            focus_test_ok=True,
            context_payload={},
            validate_summary="passed",
            focus_test_summary="passed",
        ),
    )

    result = runner.invoke(app, ["forge", "--spec", str(spec_path), "--json"])

    assert result.exit_code == 0
    events = [json.loads(line) for line in result.stdout.splitlines() if line.strip()]
    assert events[0]["event"] == "start"
    assert any(event["event"] == "phase_start" for event in events)
    assert any(event["event"] == "phase_result" for event in events)
    assert events[-1]["event"] == "result"
