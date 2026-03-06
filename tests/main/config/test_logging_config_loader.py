"""logging_config_loader 单元测试。"""

from pathlib import Path

from src.main.config.logging_config_loader import (
    get_logger_level_overrides,
    get_strategy_fallback_level_name,
    resolve_logging_config_path,
)


def test_resolve_logging_config_path_absolute(tmp_path: Path) -> None:
    config_path = tmp_path / "logging.toml"
    resolved = resolve_logging_config_path(str(config_path))
    assert resolved == config_path


def test_get_logger_level_overrides_filters_invalid_values(tmp_path: Path) -> None:
    config_path = tmp_path / "logging.toml"
    config_path.write_text(
        """
[logger_levels]
"foo.logger" = "debug"
"bar.logger" = "WARNING"
"invalid.logger" = "TRACE"
invalid_type = 123
""".strip(),
        encoding="utf-8",
    )

    overrides = get_logger_level_overrides(str(config_path))
    assert overrides == {
        "foo.logger": "DEBUG",
        "bar.logger": "WARNING",
    }


def test_get_strategy_fallback_level_name_default_and_configured(tmp_path: Path) -> None:
    missing_path = tmp_path / "missing.toml"
    assert get_strategy_fallback_level_name(str(missing_path)) == "INFO"

    config_path = tmp_path / "logging.toml"
    config_path.write_text(
        """
[settings]
strategy_fallback_level = "error"
""".strip(),
        encoding="utf-8",
    )

    assert get_strategy_fallback_level_name(str(config_path)) == "ERROR"
