"""
logging_setup.py - 日志处理模块

负责配置全局日志系统，支持控制台和文件输出。
"""
import logging
import logging.handlers
from pathlib import Path
from typing import Optional

from src.main.config.logging_config_loader import get_logger_level_overrides


def _safe_level(level_name: str) -> int:
    return getattr(logging, str(level_name).strip().upper(), logging.INFO)


def _apply_logger_level_overrides(logger_level_overrides: dict[str, str]) -> None:
    for logger_name, level_name in logger_level_overrides.items():
        level = _safe_level(level_name)
        target = logging.getLogger() if logger_name.lower() == "root" else logging.getLogger(logger_name)
        target.setLevel(level)


def setup_logging(
    log_level: str,
    log_dir: str,
    log_name: str = "strategy.log",
    logging_config_path: Optional[str] = None,
) -> None:
    """
    配置日志系统
    
    Args:
        log_level: 日志级别
        log_dir: 日志目录
        log_name: 日志文件名 (默认: strategy.log)
    """
    
    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)
    
    log_file = log_path / log_name
    
    # 移除所有现有的 handlers
    root = logging.getLogger()
    if root.handlers:
        for handler in list(root.handlers):
            handler.close()
            root.removeHandler(handler)
    
    # 每天一个日志文件，保留 30 天
    file_handler = logging.handlers.TimedRotatingFileHandler(
        filename=str(log_file),
        when="midnight",
        interval=1,
        backupCount=30,
        encoding="utf-8",
        delay=True
    )
    file_handler.suffix = "%Y%m%d"  # 设置后缀格式
    
    logging.basicConfig(
        level=_safe_level(log_level),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            file_handler,
            logging.StreamHandler()
        ]
    )

    # 覆盖指定 logger 级别（含 root，可用于按环境细分噪声）
    overrides = get_logger_level_overrides(logging_config_path)
    if overrides:
        _apply_logger_level_overrides(overrides)
