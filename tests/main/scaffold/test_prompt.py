from __future__ import annotations

from pathlib import Path

import click

import src.main.scaffold.prompt as prompt_module
from src.main.scaffold.models import CapabilityKey, CapabilityOptionKey, CreateOptions
from src.main.scaffold.prompt import prompt_for_create_options, should_prompt_for_create


def test_prompt_for_create_options_prints_refined_wizard_copy(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    prompt_answers = {
        "项目名称": "alpha_lab",
        "预设编号": "custom",
    }
    confirm_calls: list[tuple[str, bool]] = []

    def fake_prompt(text: str, **_: object) -> str:
        return prompt_answers[text]

    def fake_confirm(text: str, default: bool, **_: object) -> bool:
        confirm_calls.append((text, default))
        return default

    monkeypatch.setattr(click, "prompt", fake_prompt)
    monkeypatch.setattr(click, "confirm", fake_confirm)

    result = prompt_for_create_options(CreateOptions(name=None, destination=tmp_path))

    captured = capsys.readouterr().out

    assert "欢迎使用 option-scaffold 项目创建向导。" in captured
    assert "第 2 步 · 选择策略预设" in captured
    assert "- custom（默认） · Custom: 生成最小自定义策略骨架，按能力逐步补齐。" in captured
    assert "第 3 步 · 是否自定义模块" in captured
    assert "将直接使用当前预设的默认模块组合，不再逐项询问 capability / option。" in captured
    assert "第 6 步 · 最终确认" in captured
    assert result.name == "alpha_lab"
    assert result.preset == "custom"
    assert result.include_capabilities == (
        CapabilityKey.SELECTION,
        CapabilityKey.MONITORING,
        CapabilityKey.OBSERVABILITY,
    )
    assert result.include_options == (
        CapabilityOptionKey.FUTURE_SELECTION,
        CapabilityOptionKey.OPTION_CHAIN,
        CapabilityOptionKey.OPTION_SELECTOR,
        CapabilityOptionKey.MONITORING,
        CapabilityOptionKey.DECISION_OBSERVABILITY,
    )
    assert ("是否自定义模块", False) in confirm_calls
    assert ("确认开始生成项目吗", True) in confirm_calls
    assert not any(text.startswith("是否启用「") for text, _ in confirm_calls)
    assert not any(text.startswith("是否启用子项「") for text, _ in confirm_calls)


def test_prompt_for_create_options_prints_clearer_directory_conflict_copy(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    target_root = tmp_path / "alpha_lab"
    target_root.mkdir()
    (target_root / "keep.txt").write_text("keep", encoding="utf-8")

    prompt_answers = {
        "项目名称": "alpha_lab",
        "预设编号": "custom",
        "目录处理策略": "clear",
    }
    def fake_prompt(text: str, **_: object) -> str:
        return prompt_answers[text]

    def fake_confirm(text: str, default: bool, **_: object) -> bool:
        if text == "确认开始生成项目吗":
            return True
        return default

    monkeypatch.setattr(click, "prompt", fake_prompt)
    monkeypatch.setattr(click, "confirm", fake_confirm)

    result = prompt_for_create_options(CreateOptions(name=None, destination=tmp_path))

    captured = capsys.readouterr().out

    assert "第 5 步 · 处理已有目录" in captured
    assert "检测到目标目录已存在且非空" in captured
    assert "- clear：清空目标目录后重新生成，会删除目录中的现有文件。" in captured
    assert "第 6 步 · 最终确认" in captured
    assert "- 目录处理策略：clear（清空目标目录后重新生成）" in captured
    assert result.clear is True
    assert result.overwrite is False


def test_should_prompt_for_create_considers_option_level_overrides(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(prompt_module, "supports_interactive_prompt", lambda: True)

    should_prompt = should_prompt_for_create(
        CreateOptions(
            name="alpha_lab",
            destination=tmp_path,
            preset="custom",
            include_options=(),
            exclude_options=(),
        )
    )
    should_not_prompt = should_prompt_for_create(
        CreateOptions(
            name="alpha_lab",
            destination=tmp_path,
            preset="custom",
            include_options=(CapabilityOptionKey.FUTURE_SELECTION,),
        )
    )

    assert should_prompt is True
    assert should_not_prompt is False


def test_prompt_for_create_options_supports_auto_fix_preview(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    prompt_answers = {
        "项目名称": "auto_fix_lab",
        "预设编号": "custom",
    }

    def fake_prompt(text: str, **_: object) -> str:
        return prompt_answers[text]

    def fake_confirm(text: str, default: bool, **_: object) -> bool:
        if text == "是否自定义模块":
            return True
        if text == "是否启用「对冲能力」模块":
            return True
        if text == "是否启用子项「Delta 对冲」":
            return True
        if text == "是否启用子项「Vega 对冲」":
            return False
        if text == "是否应用上述自动修复建议":
            return True
        if text == "确认开始生成项目吗":
            return True
        return default

    monkeypatch.setattr(click, "prompt", fake_prompt)
    monkeypatch.setattr(click, "confirm", fake_confirm)

    result = prompt_for_create_options(CreateOptions(name=None, destination=tmp_path))

    captured = capsys.readouterr().out

    assert "自动修复预览" in captured
    assert "将自动启用" in captured
    assert CapabilityKey.GREEKS_RISK in result.include_capabilities
    assert CapabilityOptionKey.GREEKS_CALCULATOR in result.include_options
    assert CapabilityOptionKey.DELTA_HEDGING in result.include_options


def test_prompt_for_create_options_can_cancel_at_final_confirmation(
    tmp_path: Path,
    monkeypatch,
) -> None:
    prompt_answers = {
        "项目名称": "alpha_lab",
        "预设编号": "custom",
    }

    def fake_prompt(text: str, **_: object) -> str:
        return prompt_answers[text]

    def fake_confirm(text: str, default: bool, **_: object) -> bool:
        if text == "确认开始生成项目吗":
            return False
        return default

    monkeypatch.setattr(click, "prompt", fake_prompt)
    monkeypatch.setattr(click, "confirm", fake_confirm)

    try:
        prompt_for_create_options(CreateOptions(name=None, destination=tmp_path))
    except ValueError as exc:
        assert "已取消生成" in str(exc)
    else:
        raise AssertionError("expected ValueError when final confirmation is cancelled")
