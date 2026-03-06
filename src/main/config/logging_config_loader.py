"""logging_config_loader.py - 日志配置加载器

支持从 `config/logging/logging.toml` 加载:
1. 独立策略 logger 的回退级别
2. 指定 logger 的级别覆盖
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Dict, Optional

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib


_VALID_LEVEL_NAMES = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL", "NOTSET"}


def _project_root() -> Path:
    # src/main/config/logging_config_loader.py -> project_root
    return Path(__file__).resolve().parents[4]


def resolve_logging_config_path(path: Optional[str] = None) -> Path:
    """解析日志配置路径（支持环境变量覆盖）。"""
    raw = path or os.getenv("LOGGING_CONFIG_PATH") or "config/logging/logging.toml"
    candidate = Path(raw)
    if candidate.is_absolute():
        return candidate
    return (_project_root() / candidate).resolve()


def load_logging_config(path: Optional[str] = None) -> dict:
    """加载日志 TOML 配置，不存在或解析失败时返回空字典。"""
    config_path = resolve_logging_config_path(path)
    if not config_path.exists():
        return {}

    try:
        with open(config_path, "rb") as f:
            data = tomllib.load(f)
            return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _normalize_level_name(level: object) -> Optional[str]:
    if not isinstance(level, str):
        return None
    upper = level.strip().upper()
    if upper in _VALID_LEVEL_NAMES:
        return upper
    return None


def get_strategy_fallback_level_name(path: Optional[str] = None) -> str:
    """获取独立策略 logger 的回退级别名称。"""
    config = load_logging_config(path)
    settings = config.get("settings", {}) if isinstance(config, dict) else {}
    level_name = _normalize_level_name(
        settings.get("strategy_fallback_level") if isinstance(settings, dict) else None
    )
    return level_name or "INFO"


def get_logger_level_overrides(path: Optional[str] = None) -> Dict[str, str]:
    """获取 logger 级别覆盖表（name -> LEVEL）。"""
    config = load_logging_config(path)
    section = config.get("logger_levels", {}) if isinstance(config, dict) else {}
    if not isinstance(section, dict):
        return {}

    result: Dict[str, str] = {}
    for name, level in section.items():
        if not isinstance(name, str) or not name.strip():
            continue
        level_name = _normalize_level_name(level)
        if not level_name:
            continue
        result[name.strip()] = level_name
    return result

