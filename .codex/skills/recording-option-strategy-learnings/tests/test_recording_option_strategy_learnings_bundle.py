from __future__ import annotations

from pathlib import Path
import os
import re
import subprocess
import sys


SKILL_ROOT = Path(__file__).resolve().parents[1]


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_skill_bundle_contains_required_files() -> None:
    required_paths = [
        SKILL_ROOT / "SKILL.md",
        SKILL_ROOT / "agents" / "openai.yaml",
        SKILL_ROOT / "references" / "entry-template.md",
        SKILL_ROOT / "references" / "extraction-checklist.md",
    ]

    missing = [path for path in required_paths if not path.exists()]
    assert missing == []


def test_skill_frontmatter_and_core_rules_are_present() -> None:
    content = read_text(SKILL_ROOT / "SKILL.md")
    match = re.match(r"^---\nname: ([^\n]+)\ndescription: ([^\n]+)\n---\n", content)

    assert match is not None
    assert match.group(1).strip() == "recording-option-strategy-learnings"

    description = match.group(2).strip().strip('"')
    assert description.startswith("Use when")
    assert "plan mode" in description
    assert "docs/learnt" in description
    assert "option strategy" in description

    required_phrases = [
        "docs/learnt/YYYY-MM-DD-<topic>.md",
        "场景拆分",
        "外部冻结",
        "STM 自有在途覆盖",
        "available == 0",
        "claim",
        "bucket",
        "未同步成交",
        "## Output Contract",
        "## Pressure Scenarios",
    ]

    for phrase in required_phrases:
        assert phrase in content


def test_reference_files_cover_template_and_focus_points() -> None:
    template = read_text(SKILL_ROOT / "references" / "entry-template.md")
    checklist = read_text(SKILL_ROOT / "references" / "extraction-checklist.md")

    template_phrases = [
        "# 标题",
        "## 触发问题",
        "## 场景拆分",
        "## 设计规则",
        "## 忽略后的风险",
        "## 验证清单",
    ]

    checklist_phrases = [
        "语义边界",
        "所有权",
        "状态归属",
        "快照不足以判断",
        "释放条件",
        "回归用例",
    ]

    for phrase in template_phrases:
        assert phrase in template

    for phrase in checklist_phrases:
        assert phrase in checklist


def test_skill_bundle_passes_quick_validate() -> None:
    script_path = (
        Path.home()
        / ".codex"
        / "skills"
        / ".system"
        / "skill-creator"
        / "scripts"
        / "quick_validate.py"
    )
    env = os.environ.copy()
    env["PYTHONUTF8"] = "1"

    completed = subprocess.run(
        [sys.executable, str(script_path), str(SKILL_ROOT)],
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )

    assert completed.returncode == 0, completed.stdout + completed.stderr
