from __future__ import annotations

from pathlib import Path

from src.main.focus.service import DEFAULT_EDITABLE_PATHS, DEFAULT_FROZEN_PATHS, DEFAULT_REFERENCE_PATHS

PACK_FIXTURES: dict[str, dict[str, object]] = {
    "kernel": {
        "depends_on": (),
        "owned_paths": ("src/strategy/strategy_entry.py", "tests/cli/test_app.py"),
        "config_keys": ("strategies",),
        "test_selectors": ("tests/cli/test_app.py",),
        "commands": ("option-scaffold validate --config config/strategy_config.toml",),
        "agent_notes": ("任何策略都依赖 kernel。",),
    },
    "selection": {
        "depends_on": ("kernel",),
        "owned_paths": ("src/strategy/domain/domain_service/selection", "tests/strategy/domain/domain_service/test_selection_integration.py"),
        "config_keys": ("service_activation.option_selector",),
        "test_selectors": ("tests/strategy/domain/domain_service/test_selection_integration.py",),
        "commands": ("option-scaffold validate --config config/strategy_config.toml",),
        "agent_notes": ("选标逻辑优先落在 selection 服务。",),
    },
    "pricing": {
        "depends_on": ("kernel", "selection"),
        "owned_paths": ("src/strategy/domain/domain_service/pricing", "tests/strategy/domain/domain_service/test_pricing_engine.py"),
        "config_keys": ("service_activation.pricing_engine",),
        "test_selectors": ("tests/strategy/domain/domain_service/test_pricing_engine.py",),
        "commands": ("option-scaffold validate --config config/strategy_config.toml",),
        "agent_notes": ("定价逻辑保持在 pricing pack。",),
    },
    "risk": {
        "depends_on": ("kernel", "selection"),
        "owned_paths": ("src/strategy/domain/domain_service/risk", "tests/strategy/domain/domain_service/risk"),
        "config_keys": ("greeks_risk",),
        "test_selectors": ("tests/strategy/domain/domain_service/risk",),
        "commands": ("option-scaffold validate --config config/strategy_config.toml",),
        "agent_notes": ("风控逻辑直接修改具体 risk 服务。",),
    },
    "execution": {
        "depends_on": ("kernel", "risk"),
        "owned_paths": ("src/strategy/domain/domain_service/execution", "tests/strategy/domain/domain_service/test_execution_integration.py"),
        "config_keys": ("order_execution",),
        "test_selectors": ("tests/strategy/domain/domain_service/test_execution_integration.py",),
        "commands": ("option-scaffold run --config config/strategy_config.toml --paper",),
        "agent_notes": ("执行逻辑不要再套一层 facade。",),
    },
    "hedging": {
        "depends_on": ("kernel", "risk", "execution"),
        "owned_paths": ("src/strategy/domain/domain_service/hedging", "tests/strategy/domain/domain_service/test_delta_hedging_service.py"),
        "config_keys": ("hedging",),
        "test_selectors": ("tests/strategy/domain/domain_service/test_delta_hedging_service.py",),
        "commands": ("option-scaffold run --config config/strategy_config.toml --paper",),
        "agent_notes": ("对冲逻辑放在 hedging 服务内。",),
    },
    "monitoring": {
        "depends_on": ("kernel",),
        "owned_paths": ("src/strategy/infrastructure/monitoring", "tests/strategy/infrastructure/monitoring"),
        "config_keys": ("observability",),
        "test_selectors": ("tests/strategy/infrastructure/monitoring",),
        "commands": ("option-scaffold run --config config/strategy_config.toml --paper",),
        "agent_notes": ("监控与持久化留在基础设施层。",),
    },
    "web": {
        "depends_on": ("kernel", "monitoring"),
        "owned_paths": ("src/web", "tests/web"),
        "config_keys": ("runtime.log_dir",),
        "test_selectors": ("tests/web",),
        "commands": ("python src/web/app.py",),
        "agent_notes": ("Web 只负责读状态与展示。",),
    },
    "deploy": {
        "depends_on": ("kernel", "monitoring", "web"),
        "owned_paths": ("deploy", ".env.example"),
        "config_keys": (),
        "test_selectors": (),
        "commands": ("docker compose --env-file deploy/.env -f deploy/docker-compose.yml up -d --build",),
        "agent_notes": ("本地迭代优先不要先动 deploy。",),
    },
    "backtest": {
        "depends_on": ("kernel", "selection"),
        "owned_paths": ("src/backtesting", "tests/backtesting"),
        "config_keys": ("strategies",),
        "test_selectors": ("tests/backtesting",),
        "commands": ("option-scaffold backtest --config config/strategy_config.toml --start 2025-01-01 --end 2025-03-01 --no-chart",),
        "agent_notes": ("回测优先复用主策略契约。",),
    },
}

ADDITIONAL_FILE_PATHS: tuple[str, ...] = (
    ".dockerignore",
    ".env.example",
    "README.md",
    "LICENSE",
    "config/pytest.ini",
    "src/main/main.py",
    "src/web/app.py",
    "tests/cli/test_app.py",
    "tests/strategy/domain/domain_service/test_selection_integration.py",
    "tests/strategy/domain/domain_service/test_pricing_engine.py",
    "tests/strategy/domain/domain_service/test_execution_integration.py",
    "tests/strategy/domain/domain_service/test_delta_hedging_service.py",
)

ADDITIONAL_DIR_PATHS: tuple[str, ...] = (
    "config/domain_service",
    "config/general",
    "config/logging",
    "config/subscription",
    "config/timeframe",
    "deploy",
    "doc",
    "src/backtesting",
    "src/cli",
    "src/main/bootstrap",
    "src/main/config",
    "src/main/process",
    "src/main/scaffold",
    "src/main/utils",
    "src/strategy/application",
    "src/strategy/domain",
    "src/strategy/domain/entity",
    "src/strategy/domain/value_object",
    "src/strategy/domain/domain_service/signal",
    "src/strategy/domain/domain_service/selection",
    "src/strategy/domain/domain_service/pricing",
    "src/strategy/domain/domain_service/risk",
    "src/strategy/domain/domain_service/combination",
    "src/strategy/domain/domain_service/execution",
    "src/strategy/domain/domain_service/hedging",
    "src/strategy/infrastructure/bar_pipeline",
    "src/strategy/infrastructure/subscription",
    "src/strategy/infrastructure/utils",
    "src/strategy/infrastructure/monitoring",
    "src/strategy/infrastructure/persistence",
    "tests/backtesting",
    "tests/strategy/application",
    "tests/strategy/domain/entity",
    "tests/strategy/domain/value_object",
    "tests/strategy/domain/domain_service/risk",
    "tests/strategy/domain/domain_service/combination",
    "tests/strategy/infrastructure/bar_pipeline",
    "tests/strategy/infrastructure/subscription",
    "tests/strategy/infrastructure/utils",
    "tests/strategy/infrastructure/monitoring",
    "tests/strategy/infrastructure/persistence",
    "tests/main/scaffold",
    "tests/main/focus",
    "tests/web",
    ".codex",
    ".git",
    ".venv",
    ".pytest_cache",
    ".hypothesis",
    "temp",
)

FILE_LIKE_PATHS: set[str] = {
    ".dockerignore",
    ".env.example",
    "LICENSE",
    "README.md",
    "config/pytest.ini",
}


def _write(path: Path, content: str = "") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _render_pack_toml(pack_key: str, payload: dict[str, object]) -> str:
    def render_list(items: tuple[str, ...]) -> str:
        return "[" + ", ".join(f'"{item}"' for item in items) + "]"

    return "\n".join(
        [
            f'key = "{pack_key}"',
            f"depends_on = {render_list(payload['depends_on'])}",
            f"owned_paths = {render_list(payload['owned_paths'])}",
            f"config_keys = {render_list(payload['config_keys'])}",
            f"test_selectors = {render_list(payload['test_selectors'])}",
            f"commands = {render_list(payload['commands'])}",
            f"agent_notes = {render_list(payload['agent_notes'])}",
            "",
        ]
    )


def build_fake_focus_repo(repo_root: Path) -> Path:
    for relative_path in (*DEFAULT_EDITABLE_PATHS, *DEFAULT_REFERENCE_PATHS, *DEFAULT_FROZEN_PATHS):
        path = repo_root / relative_path
        if path.suffix or relative_path in FILE_LIKE_PATHS:
            _write(path, "")
        else:
            path.mkdir(parents=True, exist_ok=True)

    for relative_path in ADDITIONAL_DIR_PATHS:
        (repo_root / relative_path).mkdir(parents=True, exist_ok=True)

    for relative_path in ADDITIONAL_FILE_PATHS:
        _write(repo_root / relative_path, "[pytest]\n" if relative_path == "config/pytest.ini" else "")

    for pack_key, payload in PACK_FIXTURES.items():
        _write(repo_root / "focus" / "packs" / pack_key / "pack.toml", _render_pack_toml(pack_key, payload))

    return repo_root


def write_current_manifest(repo_root: Path, strategy_name: str, manifest_content: str) -> Path:
    manifest_path = repo_root / "focus" / "strategies" / strategy_name / "strategy.manifest.toml"
    _write(manifest_path, manifest_content)
    _write(
        repo_root / ".focus" / "current.toml",
        f'strategy = "{strategy_name}"\nmanifest_path = "focus/strategies/{strategy_name}/strategy.manifest.toml"\n',
    )
    return manifest_path
