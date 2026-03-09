"""整仓库脚手架 next steps 文案。"""

from __future__ import annotations


DEFAULT_CONFIG_PATH = "config/strategy_config.toml"


def build_next_step_commands(project_dir_name: str) -> tuple[str, ...]:
    """返回统一的 next steps 命令列表。"""
    return (
        f"cd {project_dir_name}",
        f"option-scaffold validate --config {DEFAULT_CONFIG_PATH}",
        f"option-scaffold run --config {DEFAULT_CONFIG_PATH}",
    )
