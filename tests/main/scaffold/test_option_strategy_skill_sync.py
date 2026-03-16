from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
CANONICAL_SKILL_DIR = ROOT / ".agents" / "skills" / "option-strategy-builder"
CODEX_SKILL_DIR = ROOT / ".codex" / "skills" / "build-option-strategy"
CLAUDE_SKILL_DIR = ROOT / ".claude" / "skills" / "option-strategy-builder"
CLAUDE_AGENT_FILE = ROOT / ".claude" / "agents" / "option-strategy-builder.md"

REFERENCE_FILES = (
    "architecture-patterns.md",
    "schema-and-persistence.md",
    "example-optionforge.md",
)

CORE_BANNED_TOKENS = (
    "OptionForge",
    "Codex",
    "src/strategy/",
    ".focus",
    "strategy_spec.toml",
    "vn.py",
)


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8").replace("\r\n", "\n")


def _split_frontmatter(text: str) -> tuple[str, str]:
    match = re.match(r"^---\n(.*?)\n---\n", text, re.DOTALL)
    assert match is not None, "markdown file must start with YAML frontmatter"
    return match.group(1), text[match.end():]


def test_canonical_skill_is_platform_neutral() -> None:
    files_to_check = (
        CANONICAL_SKILL_DIR / "SKILL.md",
        CANONICAL_SKILL_DIR / "references" / "architecture-patterns.md",
        CANONICAL_SKILL_DIR / "references" / "schema-and-persistence.md",
    )

    for path in files_to_check:
        text = _read_text(path)
        for token in CORE_BANNED_TOKENS:
            assert token not in text, f"{token!r} leaked into {path}"


def test_optionforge_example_is_repo_specific_and_optional() -> None:
    text = _read_text(CANONICAL_SKILL_DIR / "references" / "example-optionforge.md")
    assert "optional example" in text.lower()
    assert "OptionForge" in text


def test_codex_adapter_matches_canonical_body() -> None:
    canonical_frontmatter, canonical_body = _split_frontmatter(
        _read_text(CANONICAL_SKILL_DIR / "SKILL.md")
    )
    codex_frontmatter, codex_body = _split_frontmatter(
        _read_text(CODEX_SKILL_DIR / "SKILL.md")
    )

    assert canonical_body == codex_body
    assert "name: option-strategy-builder" in canonical_frontmatter
    assert "name: build-option-strategy" in codex_frontmatter


def test_claude_skill_mirror_matches_canonical() -> None:
    assert _read_text(CLAUDE_SKILL_DIR / "SKILL.md") == _read_text(
        CANONICAL_SKILL_DIR / "SKILL.md"
    )

    for filename in REFERENCE_FILES:
        assert _read_text(CLAUDE_SKILL_DIR / "references" / filename) == _read_text(
            CANONICAL_SKILL_DIR / "references" / filename
        )


def test_codex_reference_mirror_matches_canonical() -> None:
    for filename in REFERENCE_FILES:
        assert _read_text(CODEX_SKILL_DIR / "references" / filename) == _read_text(
            CANONICAL_SKILL_DIR / "references" / filename
        )


def test_claude_wrapper_targets_skill() -> None:
    frontmatter, body = _split_frontmatter(_read_text(CLAUDE_AGENT_FILE))
    assert "name: option-strategy-builder" in frontmatter
    assert "skills:" in frontmatter
    assert "option-strategy-builder" in frontmatter
    assert "Use the `option-strategy-builder` skill" in body


def test_codex_openai_metadata_stays_generic() -> None:
    text = _read_text(CODEX_SKILL_DIR / "agents" / "openai.yaml")
    for token in CORE_BANNED_TOKENS:
        assert token not in text, f"{token!r} leaked into openai metadata"
