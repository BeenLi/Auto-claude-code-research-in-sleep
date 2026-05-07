from __future__ import annotations

import re
import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
MAIN_SKILLS = REPO_ROOT / "skills"
CODEX_SKILLS = REPO_ROOT / "skills" / "skills-codex"
CLAUDE_OVERLAY = REPO_ROOT / "skills" / "skills-codex-claude-review"
GEMINI_OVERLAY = REPO_ROOT / "skills" / "skills-codex-gemini-review"
SYNC_SCRIPT = REPO_ROOT / "tools" / "sync_codex_skill_mirror.py"


def skill_names(root: Path) -> set[str]:
    return {path.parent.name for path in root.glob("*/SKILL.md")}


def main_skill_names() -> set[str]:
    return {
        path.parent.name
        for path in MAIN_SKILLS.glob("*/SKILL.md")
        if not path.parent.name.startswith("skills-codex")
    }


def read(path: Path) -> str:
    return path.read_text()


def test_codex_skill_set_matches_mainline() -> None:
    main_names = main_skill_names()
    codex_names = skill_names(CODEX_SKILLS)

    assert main_names == codex_names
    assert "prior-art-search" in codex_names


def test_codex_mirror_has_no_codex_mcp_tool_names() -> None:
    failures: list[str] = []
    pattern = re.compile(r"mcp__codex__codex(?:-reply)?")

    for markdown_file in CODEX_SKILLS.rglob("*.md"):
        text = read(markdown_file)
        if pattern.search(text):
            failures.append(str(markdown_file.relative_to(REPO_ROOT)))

    assert not failures, "Codex mirror must use subagent wording, not Codex MCP tool names:\n" + "\n".join(
        failures
    )


def test_codex_mirror_uses_subagent_tool_names_when_needed() -> None:
    reviewer_skills = {
        "ablation-planner",
        "auto-review-loop",
        "idea-creator",
        "research-review",
        "research-refine",
    }

    for skill in reviewer_skills:
        text = read(CODEX_SKILLS / skill / "SKILL.md")
        assert "spawn_agent" in text

    multi_round_skills = {"auto-review-loop", "research-refine"}
    for skill in multi_round_skills:
        text = read(CODEX_SKILLS / skill / "SKILL.md")
        assert "send_input" in text


def test_codex_shared_reference_links_exist() -> None:
    failures: list[str] = []
    pattern = re.compile(r"\.\./shared-references/([A-Za-z0-9._-]+\.md)")

    for skill_file in CODEX_SKILLS.glob("*/SKILL.md"):
        text = read(skill_file)
        for ref_name in pattern.findall(text):
            if not (CODEX_SKILLS / "shared-references" / ref_name).exists():
                failures.append(f"{skill_file.relative_to(REPO_ROOT)} -> shared-references/{ref_name}")

    assert not failures, "Codex skill shared-reference links must resolve inside skills-codex:\n" + "\n".join(
        failures
    )


def test_codex_overlay_boundaries_are_not_mirrored() -> None:
    expected_claude = {
        "auto-paper-improvement-loop",
        "auto-review-loop",
        "novelty-check",
        "paper-figure",
        "paper-plan",
        "paper-write",
        "research-refine",
        "research-review",
    }
    expected_gemini = {
        "auto-paper-improvement-loop",
        "auto-review-loop",
        "grant-proposal",
        "idea-creator",
        "idea-discovery",
        "novelty-check",
        "paper-figure",
        "paper-plan",
        "paper-poster",
        "paper-slides",
        "paper-write",
        "paper-writing",
        "research-refine",
        "research-review",
    }

    assert skill_names(CLAUDE_OVERLAY) == expected_claude
    assert skill_names(GEMINI_OVERLAY) == expected_gemini


def test_codex_mirror_sync_is_clean_after_apply() -> None:
    result = subprocess.run(
        ["python3", str(SYNC_SCRIPT), "--dry-run"],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=True,
    )

    assert "changes: 0" in result.stdout
