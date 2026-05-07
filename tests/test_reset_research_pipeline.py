from __future__ import annotations

import os
import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "tools" / "reset_research_pipeline.sh"


PIPELINE_STATUS = """# AGENT.md

Intro text.

## Pipeline Status

```yaml
stage: implementation
idea: old idea
active_tasks: [run]
```

## State Persistence Rules

Keep this section.
"""


DELETE_DIRS = [
    "idea-stage",
    "refine-logs",
    "review-stage",
    "experiments",
    "paper",
    "figures",
    "rebuttal",
    ".aris/traces",
]

DELETE_FILES = [
    "NARRATIVE_REPORT.md",
    "PAPER_PLAN.md",
    "CLAIMS_FROM_RESULTS.md",
    "findings.md",
    "MANIFEST.md",
    "ISSUE_BOARD.md",
    "STRATEGY_PLAN.md",
]


def run_script(project: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", str(SCRIPT), str(project), *args],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=check,
    )


def make_project(tmp_path: Path) -> Path:
    project = tmp_path / "project"
    project.mkdir()
    (project / "AGENT.md").write_text(PIPELINE_STATUS)
    (project / "AGENTS.md").symlink_to("AGENT.md")
    (project / "CLAUDE.md").symlink_to("AGENT.md")

    for rel in DELETE_DIRS:
        path = project / rel
        path.mkdir(parents=True, exist_ok=True)
        (path / "artifact.txt").write_text(rel)

    for rel in DELETE_FILES:
        path = project / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(rel)

    aris = project / ".aris"
    aris.mkdir(exist_ok=True)
    (aris / "installed-skills.txt").write_text("manifest\n")
    (aris / "installed-skills-codex.txt").write_text("codex manifest\n")
    (aris / "meta").mkdir(exist_ok=True)
    (aris / "meta" / "events.jsonl").write_text("{}\n")
    tools_target = tmp_path / "tools-target"
    tools_target.mkdir()
    (aris / "tools").symlink_to(tools_target)

    (project / "research-wiki").mkdir()
    (project / "research-wiki" / "keep.md").write_text("persistent\n")
    return project


def assert_pipeline_status_reset(agent_text: str) -> None:
    assert "## Pipeline Status" in agent_text
    assert "```yaml\n{}\n```" in agent_text
    assert "stage: implementation" not in agent_text
    assert "## State Persistence Rules" in agent_text


def test_dry_run_reports_actions_without_mutating_project(tmp_path: Path) -> None:
    project = make_project(tmp_path)
    before_agent = (project / "AGENT.md").read_text()

    result = run_script(project)

    assert "ARIS Research Pipeline Reset" in result.stdout
    assert "Action:    dry-run" in result.stdout
    assert "REMOVE dir  idea-stage" in result.stdout
    assert "RESET AGENT.md Pipeline Status -> {}" in result.stdout
    assert (project / "AGENT.md").read_text() == before_agent
    for rel in DELETE_DIRS + DELETE_FILES:
        assert (project / rel).exists(), f"dry-run must not remove {rel}"


def test_apply_removes_pipeline_artifacts_and_preserves_aris_install_state(tmp_path: Path) -> None:
    project = make_project(tmp_path)

    result = run_script(project, "--apply")

    assert "Action:    apply" in result.stdout
    for rel in DELETE_DIRS + DELETE_FILES:
        assert not (project / rel).exists(), f"apply must remove {rel}"
    assert (project / ".aris" / "installed-skills.txt").exists()
    assert (project / ".aris" / "installed-skills-codex.txt").exists()
    assert (project / ".aris" / "tools").is_symlink()
    assert (project / ".aris" / "meta" / "events.jsonl").exists()
    assert (project / "research-wiki" / "keep.md").exists()

    assert_pipeline_status_reset((project / "AGENT.md").read_text())
    assert_pipeline_status_reset((project / "AGENTS.md").read_text())
    assert_pipeline_status_reset((project / "CLAUDE.md").read_text())


def test_apply_fails_before_deleting_when_agent_file_is_missing(tmp_path: Path) -> None:
    project = make_project(tmp_path)
    (project / "AGENT.md").unlink()

    result = run_script(project, "--apply", check=False)

    assert result.returncode != 0
    assert "AGENT.md not found" in result.stderr
    assert (project / "idea-stage").exists()
    assert (project / "MANIFEST.md").exists()


def test_apply_fails_before_deleting_when_pipeline_status_block_is_missing(tmp_path: Path) -> None:
    project = make_project(tmp_path)
    (project / "AGENT.md").write_text("# AGENT.md\n\nNo status here.\n")

    result = run_script(project, "--apply", check=False)

    assert result.returncode != 0
    assert "Pipeline Status" in result.stderr
    assert (project / "idea-stage").exists()
    assert (project / "MANIFEST.md").exists()


def test_help_succeeds() -> None:
    result = subprocess.run(
        ["bash", str(SCRIPT), "--help"],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=True,
    )

    assert "reset_research_pipeline.sh" in result.stdout
    assert "--apply" in result.stdout
