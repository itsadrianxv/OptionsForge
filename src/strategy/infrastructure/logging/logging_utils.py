import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

from src.main.config.logging_config_loader import (
    get_logger_level_overrides,
    get_strategy_fallback_level_name,
)


def _resolve_fallback_level() -> int:
    """解析独立运行时（未配置根日志）策略日志级别。"""
    level_name = os.getenv("STRATEGY_FALLBACK_LOG_LEVEL", "").strip().upper()
    if not level_name:
        level_name = get_strategy_fallback_level_name()
    return getattr(logging, level_name, logging.INFO)


def setup_strategy_logger(name: str, log_file: str = "strategy.log") -> logging.Logger:
    """
    为策略设置一个记录器，同时写入控制台和文件。
    
    参数:
        name: 记录器的名称 (例如 "VolatilityStrategy")。
        log_file: data/logs 目录中日志文件的相对路径。
                  可以包含子目录 (例如 "15m/strategy_15m.log")。
    
    返回:
        配置好的 logging.Logger 实例。
    """
    logger = logging.getLogger(name)
    logger_level_overrides = get_logger_level_overrides()
    override_level_name = logger_level_overrides.get(name)
    override_level = getattr(logging, override_level_name, None) if override_level_name else None
    
    # --- 新逻辑：检测主程序配置 ---
    # 如果根记录器已经有处理器，说明 main 已经调用了 setup_logging。
    # 我们需要将日志传播到根记录器，并避免创建冗余的处理器（防止 Windows 文件锁定）。
    root_logger = logging.getLogger()
    if root_logger.handlers:
        logger.setLevel(override_level if override_level is not None else logging.NOTSET)
        logger.propagate = True
        if logger.handlers:
            for handler in list(logger.handlers):
                handler.close()
                logger.removeHandler(handler)
        return logger
    # --------------------------------------------------
    
    # 如果记录器已配置，避免多次添加处理器
    if logger.handlers:
        for handler in list(logger.handlers):
            handler.close()
            logger.removeHandler(handler)
        
    # 确定项目根目录
    # 此文件位于 src/strategy/infrastructure/logging/logging_utils.py
    # 根目录位于 ../../../../
    current_file = Path(__file__).resolve()
    project_root = current_file.parents[4]
    
    log_dir = project_root / "data" / "logs"
    log_path = log_dir / log_file
    
    # 确保目录存在
    log_path.parent.mkdir(parents=True, exist_ok=True)
    
    # 格式化器
    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    )

    effective_level = override_level if override_level is not None else _resolve_fallback_level()
    logger.setLevel(effective_level)
    
    # 文件处理器
    # 使用 RotatingFileHandler 避免文件无限增长，虽然用户没有明确要求轮换，
    # 但这是个好习惯。最大大小 10MB，保留 10 个备份。
    file_handler = RotatingFileHandler(
        log_path, maxBytes=10*1024*1024, backupCount=10, encoding="utf-8"
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(effective_level)
    logger.addHandler(file_handler)
    
    # 控制台处理器
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.setLevel(effective_level)
    logger.addHandler(console_handler)
    
    # 防止传播到根记录器，以避免在根记录器已配置的情况下出现重复日志
    logger.propagate = False
    
    return logger
