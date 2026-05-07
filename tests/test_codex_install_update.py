from __future__ import annotations

import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
INSTALL_SCRIPT = REPO_ROOT / "tools" / "install_aris.sh"


def run(
    cmd: list[str], *, cwd: Path | None = None, check: bool = True, env: dict[str, str] | None = None
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        cwd=cwd or REPO_ROOT,
        text=True,
        capture_output=True,
        check=check,
        env=env,
    )


def make_skill(path: Path, body: str) -> None:
    path.mkdir(parents=True, exist_ok=True)
    (path / "SKILL.md").write_text(body)


def make_minimal_aris_repo(root: Path) -> Path:
    repo = root / "aris"
    make_skill(repo / "skills" / "skills-codex" / "alpha", "# alpha\n")
    make_skill(repo / "skills" / "skills-codex" / "beta", "# beta-base\n")
    (repo / "skills" / "skills-codex" / "shared-references").mkdir(parents=True, exist_ok=True)
    (repo / "skills" / "skills-codex" / "shared-references" / "reviewer-routing.md").write_text("base\n")
    make_skill(repo / "skills" / "skills-codex-claude-review" / "beta", "# beta-claude-overlay\n")
    make_skill(repo / "skills" / "skills-codex-gemini-review" / "beta", "# beta-gemini-overlay\n")
    return repo


def make_minimal_claude_aris_repo(root: Path) -> Path:
    repo = root / "aris-claude"
    make_skill(repo / "skills" / "alpha", "# alpha\n")
    (repo / "skills" / "shared-references").mkdir(parents=True, exist_ok=True)
    (repo / "skills" / "shared-references" / "reviewer-routing.md").write_text("base\n")
    return repo


def test_install_aris_codex_dry_run_has_no_project_writes(tmp_path: Path) -> None:
    repo = make_minimal_aris_repo(tmp_path)
    project = tmp_path / "project"
    project.mkdir()

    dry_run = run(
        [
            "bash",
            str(INSTALL_SCRIPT),
            str(project),
            "--target",
            "codex",
            "--aris-repo",
            str(repo),
            "--dry-run",
        ]
    )

    assert "(dry-run) no changes made" in dry_run.stdout
    assert not (project / ".aris").exists()
    assert not (project / ".agents").exists()
    assert not (project / "AGENTS.md").exists()


def test_install_aris_codex_avoids_bash4_associative_arrays() -> None:
    text = INSTALL_SCRIPT.read_text()
    assert "declare -A" not in text


def test_install_aris_default_skips_doc_update(tmp_path: Path) -> None:
    repo = make_minimal_claude_aris_repo(tmp_path)
    project = tmp_path / "project"
    project.mkdir()
    (project / "CLAUDE.md").write_text("# Existing\n")

    run(
        [
            "bash",
            str(INSTALL_SCRIPT),
            str(project),
            "--aris-repo",
            str(repo),
            "--quiet",
        ]
    )

    assert (project / ".claude" / "skills" / "alpha").is_symlink()
    assert "ARIS Skill Scope" not in (project / "CLAUDE.md").read_text()


def test_install_aris_with_doc_preserves_agent_symlink(tmp_path: Path) -> None:
    repo = make_minimal_claude_aris_repo(tmp_path)
    project = tmp_path / "project"
    project.mkdir()
    (project / "AGENT.md").write_text("# Canonical\n")
    (project / "CLAUDE.md").symlink_to("AGENT.md")

    run(
        [
            "bash",
            str(INSTALL_SCRIPT),
            str(project),
            "--aris-repo",
            str(repo),
            "--with-doc",
            "--quiet",
        ]
    )

    assert (project / "CLAUDE.md").is_symlink()
    assert "ARIS Skill Scope" in (project / "AGENT.md").read_text()


def test_install_aris_codex_reconcile_and_uninstall(tmp_path: Path) -> None:
    repo = make_minimal_aris_repo(tmp_path)
    project = tmp_path / "project"
    project.mkdir()

    run(
        [
            "bash",
            str(INSTALL_SCRIPT),
            str(project),
            "--target",
            "codex",
            "--aris-repo",
            str(repo),
            "--quiet",
        ]
    )

    manifest = project / ".aris" / "installed-skills-codex.txt"
    assert manifest.exists()
    assert not (project / "AGENTS.md").exists()
    assert (project / ".agents" / "skills" / "alpha").is_symlink()
    assert (project / ".agents" / "skills" / "beta").resolve() == (
        repo / "skills" / "skills-codex" / "beta"
    ).resolve()

    run(
        [
            "bash",
            str(INSTALL_SCRIPT),
            str(project),
            "--target",
            "codex",
            "--aris-repo",
            str(repo),
            "--reconcile",
            "--with-claude-review-overlay",
            "--quiet",
        ]
    )
    assert (project / ".agents" / "skills" / "beta").resolve() == (
        repo / "skills" / "skills-codex-claude-review" / "beta"
    ).resolve()

    (repo / "skills" / "skills-codex" / "alpha").rename(repo / "skills" / "skills-codex" / "alpha-removed")
    make_skill(repo / "skills" / "skills-codex" / "gamma", "# gamma\n")
    run(
        [
            "bash",
            str(INSTALL_SCRIPT),
            str(project),
            "--target",
            "codex",
            "--aris-repo",
            str(repo),
            "--reconcile",
            "--with-claude-review-overlay",
            "--quiet",
        ]
    )
    assert not (project / ".agents" / "skills" / "alpha").exists()
    assert (project / ".agents" / "skills" / "gamma").is_symlink()

    (project / ".agents" / "skills" / "local-only").mkdir(parents=True)
    run(
        [
            "bash",
            str(INSTALL_SCRIPT),
            str(project),
            "--target",
            "codex",
            "--aris-repo",
            str(repo),
            "--uninstall",
            "--quiet",
        ]
    )
    assert (project / ".agents" / "skills" / "local-only").exists()
    assert not (project / ".agents" / "skills" / "beta").exists()
    assert (project / ".aris" / "installed-skills-codex.txt.prev").exists()


def test_install_aris_codex_with_doc_opt_in_preserves_agent_symlink(tmp_path: Path) -> None:
    repo = make_minimal_aris_repo(tmp_path)
    project = tmp_path / "project"
    project.mkdir()
    (project / "AGENT.md").write_text("# Canonical\n")
    (project / "AGENTS.md").symlink_to("AGENT.md")

    run(
        [
            "bash",
            str(INSTALL_SCRIPT),
            str(project),
            "--target",
            "codex",
            "--aris-repo",
            str(repo),
            "--with-claude-review-overlay",
            "--with-doc",
            "--quiet",
        ]
    )

    assert (project / "AGENTS.md").is_symlink()
    agents_text = (project / "AGENTS.md").read_text()
    assert "ARIS Codex Skill Scope" in agents_text
    assert f"ARIS repo root: `{repo}`" in agents_text
    assert "repo_root" in agents_text
    assert '$1=="repo_root"{print $2; exit}' in agents_text
    assert "$1==repo_root" not in agents_text
    assert "skills-codex,skills-codex-claude-review" in agents_text
    assert "--with-claude-review-overlay --reconcile" in agents_text

    run(
        [
            "bash",
            str(INSTALL_SCRIPT),
            str(project),
            "--target",
            "codex",
            "--aris-repo",
            str(repo),
            "--uninstall",
            "--with-doc",
            "--quiet",
        ]
    )

    assert (project / "AGENTS.md").is_symlink()
    assert "ARIS Codex Skill Scope" not in (project / "AGENT.md").read_text()


def test_install_aris_codex_uninstall_uses_manifest_repo_root(tmp_path: Path) -> None:
    original_repo = make_minimal_aris_repo(tmp_path / "original")
    other_repo = make_minimal_aris_repo(tmp_path / "other")
    project = tmp_path / "project"
    project.mkdir()

    run(
        [
            "bash",
            str(INSTALL_SCRIPT),
            str(project),
            "--target",
            "codex",
            "--aris-repo",
            str(original_repo),
            "--quiet",
        ]
    )

    alpha_link = project / ".agents" / "skills" / "alpha"
    assert alpha_link.is_symlink()
    assert alpha_link.resolve() == (original_repo / "skills" / "skills-codex" / "alpha").resolve()

    run(
        [
            "bash",
            str(INSTALL_SCRIPT),
            str(project),
            "--target",
            "codex",
            "--aris-repo",
            str(other_repo),
            "--uninstall",
            "--quiet",
        ]
    )

    assert not alpha_link.exists()
    assert not (project / ".agents" / "skills" / "beta").exists()
    assert not (project / ".agents" / "skills" / "shared-references").exists()
    assert not (project / ".aris" / "installed-skills-codex.txt").exists()
    assert (project / ".aris" / "installed-skills-codex.txt.prev").exists()


def test_install_aris_codex_reconcile_removes_stale_links_from_manifest_repo(tmp_path: Path) -> None:
    original_repo = make_minimal_aris_repo(tmp_path / "original")
    new_repo = make_minimal_aris_repo(tmp_path / "new")
    (new_repo / "skills" / "skills-codex" / "alpha").rename(
        new_repo / "skills" / "skills-codex" / "alpha-removed"
    )
    make_skill(new_repo / "skills" / "skills-codex" / "gamma", "# gamma\n")
    project = tmp_path / "project"
    project.mkdir()

    run(
        [
            "bash",
            str(INSTALL_SCRIPT),
            str(project),
            "--target",
            "codex",
            "--aris-repo",
            str(original_repo),
            "--quiet",
        ]
    )

    alpha_link = project / ".agents" / "skills" / "alpha"
    beta_link = project / ".agents" / "skills" / "beta"
    assert alpha_link.is_symlink()
    assert alpha_link.resolve() == (original_repo / "skills" / "skills-codex" / "alpha").resolve()

    run(
        [
            "bash",
            str(INSTALL_SCRIPT),
            str(project),
            "--target",
            "codex",
            "--aris-repo",
            str(new_repo),
            "--reconcile",
            "--quiet",
        ]
    )

    assert not alpha_link.exists()
    assert beta_link.resolve() == (new_repo / "skills" / "skills-codex" / "beta").resolve()
    assert (project / ".agents" / "skills" / "gamma").resolve() == (
        new_repo / "skills" / "skills-codex" / "gamma"
    ).resolve()
    manifest = (project / ".aris" / "installed-skills-codex.txt").read_text()
    assert "\talpha\t" not in manifest
    assert f"repo_root\t{new_repo}" in manifest


def test_install_aris_codex_reconcile_accepts_already_deleted_stale_link(tmp_path: Path) -> None:
    original_repo = make_minimal_aris_repo(tmp_path / "original")
    new_repo = make_minimal_aris_repo(tmp_path / "new")
    (new_repo / "skills" / "skills-codex" / "alpha").rename(
        new_repo / "skills" / "skills-codex" / "alpha-removed"
    )
    project = tmp_path / "project"
    project.mkdir()

    run(
        [
            "bash",
            str(INSTALL_SCRIPT),
            str(project),
            "--target",
            "codex",
            "--aris-repo",
            str(original_repo),
            "--quiet",
        ]
    )

    alpha_link = project / ".agents" / "skills" / "alpha"
    assert alpha_link.is_symlink()
    alpha_link.unlink()

    run(
        [
            "bash",
            str(INSTALL_SCRIPT),
            str(project),
            "--target",
            "codex",
            "--aris-repo",
            str(new_repo),
            "--reconcile",
            "--quiet",
        ]
    )

    manifest = (project / ".aris" / "installed-skills-codex.txt").read_text()
    assert "\talpha\t" not in manifest


def test_install_aris_codex_gemini_overlay_and_mutual_exclusion(tmp_path: Path) -> None:
    repo = make_minimal_aris_repo(tmp_path)
    project = tmp_path / "project"
    project.mkdir()

    run(
        [
            "bash",
            str(INSTALL_SCRIPT),
            str(project),
            "--target",
            "codex",
            "--aris-repo",
            str(repo),
            "--with-gemini-review-overlay",
            "--quiet",
        ]
    )

    assert (project / ".agents" / "skills" / "beta").resolve() == (
        repo / "skills" / "skills-codex-gemini-review" / "beta"
    ).resolve()

    refused = run(
        [
            "bash",
            str(INSTALL_SCRIPT),
            str(project),
            "--target",
            "codex",
            "--aris-repo",
            str(repo),
            "--with-claude-review-overlay",
            "--with-gemini-review-overlay",
            "--dry-run",
        ],
        check=False,
    )

    assert refused.returncode != 0
    assert "mutually exclusive" in refused.stderr


def test_install_aris_gemini_target_and_doc_block(tmp_path: Path) -> None:
    repo = make_minimal_claude_aris_repo(tmp_path)
    project = tmp_path / "project"
    project.mkdir()
    (project / "GEMINI.md").write_text("# Gemini\n")

    run(
        [
            "bash",
            str(INSTALL_SCRIPT),
            str(project),
            "--target",
            "gemini",
            "--aris-repo",
            str(repo),
            "--with-doc",
            "--quiet",
        ]
    )

    assert (project / ".gemini" / "skills" / "alpha").is_symlink()
    assert (project / ".gemini" / "skills" / "alpha").resolve() == (
        repo / "skills" / "alpha"
    ).resolve()
    manifest = project / ".aris" / "installed-skills-gemini.txt"
    assert manifest.exists()
    manifest_text = manifest.read_text()
    assert "target\tgemini" in manifest_text
    assert "\t.gemini/skills/alpha\t" in manifest_text
    assert "ARIS Gemini Skill Scope" in (project / "GEMINI.md").read_text()


def test_obsolete_install_and_update_scripts_are_removed() -> None:
    obsolete = {
        "install_aris_codex.sh",
        "install_claude_skills.sh",
        "install_codex_skills.sh",
        "smart_update.sh",
        "smart_update_codex.sh",
        "smart_update.ps1",
    }

    for name in obsolete:
        assert not (REPO_ROOT / "tools" / name).exists()
