import importlib.util
from pathlib import Path

module_path = Path(__file__).resolve().parents[3] / "src" / "main" / "config" / "config_loader.py"
spec = importlib.util.spec_from_file_location("config_loader", module_path)
config_loader = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(config_loader)
ConfigLoader = config_loader.ConfigLoader


def test_extract_timeframe_name_from_new_timeframe_section() -> None:
    override = {"timeframe": {"name": "15m", "bar_window": 15, "bar_interval": "MINUTE"}}

    assert ConfigLoader.extract_timeframe_name(override, fallback="fallback") == "15m"


def test_extract_timeframe_name_uses_fallback_when_missing() -> None:
    override = {"runtime": {"log_level": "INFO"}}

    assert ConfigLoader.extract_timeframe_name(override, fallback="30m") == "30m"


def test_merge_strategy_config_applies_timeframe_bar_settings() -> None:
    base = {
        "strategies": [
            {
                "class_name": "StrategyEntry",
                "strategy_name": "volatility",
                "setting": {"max_positions": 5},
            }
        ]
    }
    override = {"timeframe": {"name": "15m", "bar_window": 15, "bar_interval": "MINUTE"}}

    merged = ConfigLoader.merge_strategy_config(base, override)

    strategy = merged["strategies"][0]
    assert strategy["strategy_name"] == "volatility_15m"
    assert strategy["setting"]["max_positions"] == 5
    assert strategy["setting"]["bar_window"] == 15
    assert strategy["setting"]["bar_interval"] == "MINUTE"
    assert strategy["setting"]["timeframe"] == "15m"


def test_merge_strategy_config_applies_default_strategy_name_for_timeframe() -> None:
    base = {"strategies": [{"class_name": "StrategyEntry", "setting": {}}]}
    override = {"timeframe": {"name": "15m", "bar_window": 15}}

    merged = ConfigLoader.merge_strategy_config(base, override)

    assert merged["strategies"][0]["strategy_name"] == "default_strategy_15m"


def test_merge_strategy_config_supports_legacy_override_structure() -> None:
    base = {
        "strategies": [
            {
                "class_name": "StrategyEntry",
                "strategy_name": "default_strategy",
                "setting": {"bar_window": 1, "bar_interval": "MINUTE"},
            }
        ]
    }
    override = {
        "strategies": [
            {
                "strategy_name": "legacy_15m",
                "setting": {"bar_window": 15, "bar_interval": "MINUTE"},
            }
        ]
    }

    merged = ConfigLoader.merge_strategy_config(base, override)

    strategy = merged["strategies"][0]
    assert strategy["strategy_name"] == "legacy_15m"
    assert strategy["setting"]["bar_window"] == 15
    assert strategy["setting"]["bar_interval"] == "MINUTE"
