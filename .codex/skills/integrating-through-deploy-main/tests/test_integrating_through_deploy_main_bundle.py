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
        SKILL_ROOT / "references" / "testing-campaign.md",
    ]

    missing = [path for path in required_paths if not path.exists()]
    assert missing == []


def test_skill_frontmatter_and_core_constraints_are_present() -> None:
    content = read_text(SKILL_ROOT / "SKILL.md")
    match = re.match(r"^---\nname: ([^\n]+)\ndescription: ([^\n]+)\n---\n", content)

    assert match is not None
    assert match.group(1).strip() == "integrating-through-deploy-main"

    description = match.group(2).strip().strip('"')
    assert description.startswith("Use when")
    assert "worktree" in description
    assert "deploy-main" in description
    assert "merge conflict" in description
    assert "Docker deployment" in description
    assert "env-sensitive changes" in description

    required_phrases = [
        ".worktrees/",
        ".worktrees/deploy-main",
        "deploy/deploy-main.ps1",
        "docker compose",
        "docker-compose",
        "docker build",
        "阶段集成",
        "冲突优先在 `deploy-main` 集成时解决",
        "只有在冲突暴露真实产品歧义时才暂停并询问",
        "docker compose config",
        "目标服务启动成功",
        "容器内关键环境变量检查成功",
        "可部署",
        "部署问题已修复",
        "临时例外",
        "违反字面就是违反精神",
        "只改了 Docker 或 env，不用重新跑 deploy 验证",
    ]

    for phrase in required_phrases:
        assert phrase in content


def test_testing_campaign_covers_red_green_refactor_and_pressure_scenarios() -> None:
    content = read_text(SKILL_ROOT / "references" / "testing-campaign.md")

    required_phrases = [
        "## RED",
        "## GREEN",
        "## REFACTOR",
        "没有 `deploy-main`",
        "分支已分叉且出现冲突",
        "修改 env-sensitive 文件",
        "先补齐并使用 `deploy-main`",
        "在阶段集成点立即解冲突",
        "命中规则时重跑部署验证",
        "临时例外",
        "遵循精神不是字面",
    ]

    for phrase in required_phrases:
        assert phrase in content


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
