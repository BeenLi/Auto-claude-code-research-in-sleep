from __future__ import annotations

import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def read(relative_path: str) -> str:
    return (REPO_ROOT / relative_path).read_text()


def workflow1_readme_section() -> str:
    text = read("README.md")
    start = text.index("### Workflow 1: Idea Discovery")
    end = text.index("### Workflow 1.5:", start)
    return text[start:end]


def research_pipeline_stage1() -> str:
    text = read("skills/research-pipeline/SKILL.md")
    start = text.index("### Stage 1: Idea Discovery")
    end = text.index("### Stage 2:", start)
    return text[start:end]


def run_tool(script: str, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [str(REPO_ROOT / "tools" / script), *args],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
    )


def run_python_tool(script: str, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["python3", str(REPO_ROOT / "tools" / script), *args],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
    )


def test_workflow1_chain_is_canonical_across_entrypoints() -> None:
    canonical = (
        "research-lit -> idea-creator -> novelty-check -> research-review -> "
        "research-refine-pipeline"
    )
    arrow_canonical = (
        "/research-lit -> /idea-creator -> /novelty-check -> /research-review -> "
        "/research-refine-pipeline"
    )

    assert canonical in read("AGENT.md")
    assert arrow_canonical in read("README.md")
    assert "/research-refine-pipeline" in read("skills/idea-discovery/SKILL.md")
    assert (
        "This internally runs: `/research-lit` -> `/idea-creator` -> "
        "`/novelty-check` -> `/research-review` -> `/research-refine-pipeline`"
        in read("skills/research-pipeline/SKILL.md")
    )
    assert "refine-logs/FINAL_PROPOSAL.md" in read("skills/research-pipeline/SKILL.md")
    assert "refine-logs/EXPERIMENT_PLAN.md" in read("skills/research-pipeline/SKILL.md")


def test_workflow1_docs_do_not_assign_execution_to_workflow1() -> None:
    workflow1_docs = "\n".join(
        [
            workflow1_readme_section(),
            read("AGENT.md"),
            read("skills/idea-discovery/SKILL.md"),
            read("skills/idea-creator/SKILL.md"),
            research_pipeline_stage1(),
        ]
    )

    forbidden = [
        "GPU pilot experiments",
        "Pilot top 2-3 ideas",
        "pilot on GPU",
        "pilots on GPU",
        "pilot experiments on GPU",
        "Rank by empirical signal",
        "ranks by empirical signal",
    ]
    for phrase in forbidden:
        assert phrase not in workflow1_docs

    assert "Workflow 1 does not run pilots or baseline reproduction" in workflow1_docs
    assert "Workflow 1.5" in workflow1_docs


def test_handoff_schema_is_single_shared_reference() -> None:
    schema = read("skills/shared-references/idea-handoff-schema.md")
    required_fields = [
        "core_baseline",
        "baseline_evaluability_score",
        "canon_mapping",
        "metrics",
        "target_validation_style",
        "evaluation_target_clarity",
        "evaluation_target_feasibility",
        "baseline_reproducibility",
        "evaluation_environment_access",
        "idea_adapter_cost",
        "pilot_runtime_cost",
        "handoff_to_workflow_1_5",
        "main_blocker",
        "negative_evidence_response",
    ]
    for field in required_fields:
        assert field in schema

    for relative_path in [
        "skills/idea-discovery/SKILL.md",
        "skills/idea-creator/SKILL.md",
        "skills/research-pipeline/SKILL.md",
        "skills/experiment-bridge/SKILL.md",
        "skills/experiment-plan/SKILL.md",
        "skills/research-refine-pipeline/SKILL.md",
        "skills/shared-references/integration-contract.md",
    ]:
        assert "shared-references/idea-handoff-schema.md" in read(relative_path)

    repeated_field_blocks = 0
    for relative_path in [
        "skills/idea-discovery/SKILL.md",
        "skills/idea-creator/SKILL.md",
        "skills/research-pipeline/SKILL.md",
    ]:
        text = read(relative_path)
        if all(field in text for field in required_fields):
            repeated_field_blocks += 1
    assert repeated_field_blocks <= 1


def test_idea_creator_owns_report_templates_and_orchestrator_links_them() -> None:
    assert (REPO_ROOT / "templates" / "IDEA_REPORT_TEMPLATE.md").exists()
    assert (REPO_ROOT / "templates" / "IDEA_CANDIDATES_TEMPLATE.md").exists()

    idea_creator = read("skills/idea-creator/SKILL.md")
    idea_discovery = read("skills/idea-discovery/SKILL.md")

    assert "templates/IDEA_REPORT_TEMPLATE.md" in idea_creator
    assert "templates/IDEA_CANDIDATES_TEMPLATE.md" in idea_creator
    assert "templates/IDEA_REPORT_TEMPLATE.md" in idea_discovery
    assert "templates/IDEA_CANDIDATES_TEMPLATE.md" in idea_discovery
    assert "# Idea Discovery Report" not in idea_discovery
    assert "# Idea Candidates" not in idea_discovery


def test_workflow1_checkpoint_reference_exists_and_is_used() -> None:
    checkpoints = read("skills/shared-references/workflow1-checkpoints.md")
    for phrase in [
        "Literature scope",
        "Idea selection",
        "Refined proposal ready",
    ]:
        assert phrase in checkpoints

    for relative_path in [
        "skills/idea-discovery/SKILL.md",
        "skills/research-pipeline/SKILL.md",
        "skills/research-refine-pipeline/SKILL.md",
    ]:
        assert "shared-references/workflow1-checkpoints.md" in read(relative_path)


def test_research_lit_landscape_pack_section_matches_idea_creator_reader() -> None:
    research_lit = read("skills/research-lit/SKILL.md")
    idea_creator = read("skills/idea-creator/SKILL.md")

    assert "`## Section 4 -- Landscape Pack`" in research_lit
    assert "Section 4" in idea_creator
    assert "Landscape Pack" in idea_creator
    assert "Section 5" not in idea_creator


def test_research_pipeline_requires_explicit_brief_path() -> None:
    stage1 = research_pipeline_stage1()

    assert "RESEARCH_BRIEF.md" in stage1
    assert "explicit" in stage1
    assert "automatically loaded" not in stage1
    assert "If `RESEARCH_BRIEF.md` exists in the project root" not in stage1


def test_reference_paper_extraction_has_single_owner() -> None:
    idea_discovery = read("skills/idea-discovery/SKILL.md")
    research_lit = read("skills/research-lit/SKILL.md")

    assert "/research-lit` handles" in idea_discovery
    assert "idea-stage/REF_PAPER_SUMMARY.md" in research_lit
    assert "### Phase 0.5: Reference Paper Summary" not in idea_discovery
    assert "Summarize the reference paper in full before searching" not in idea_discovery


def test_codex_skill_mirror_is_fresh() -> None:
    result = run_python_tool("sync_codex_skill_mirror.py", "--dry-run")

    assert result.returncode == 0
    assert "changes: 0" in result.stdout


def test_aris_cache_is_ignored() -> None:
    gitignore = read(".gitignore")

    assert ".aris/cache/" in gitignore
    assert ".aris/verify-papers/" in gitignore


def test_inject_default_sources_preserves_explicit_sources() -> None:
    result = run_tool("inject_default_sources.sh", "KV cache — sources: zotero, arxiv")

    assert result.returncode == 0
    assert result.stdout.strip() == "KV cache — sources: zotero, arxiv"
    assert result.stderr == ""


def test_inject_default_sources_adds_all_gemini_when_missing() -> None:
    result = run_tool("inject_default_sources.sh", "KV cache under CXL")

    assert result.returncode == 0
    assert result.stdout.strip() == "KV cache under CXL — sources: all, gemini"
    assert result.stderr == ""


READY_HANDOFF_HEADER = (
    "| Idea | baseline_evaluability_score | core_baseline | canon_mapping | metrics | "
    "target_validation_style | evaluation_target_clarity | evaluation_target_feasibility | "
    "evaluation_environment_access | idea_adapter_cost | pilot_runtime_cost | "
    "negative_evidence_response | handoff_to_workflow_1_5 | main_blocker |"
)
READY_HANDOFF_DIVIDER = (
    "|------|-----------------------------|---------------|---------------|---------|"
    "-------------------------|---------------------------|-------------------------------|"
    "-------------------------------|-------------------|--------------------|"
    "----------------------------|-------------------------|--------------|"
)


def _build_idea_report(row_cells: str) -> str:
    return (
        "# Research Idea Report\n"
        "\n"
        "## Evaluation Handoff Summary\n"
        f"{READY_HANDOFF_HEADER}\n"
        f"{READY_HANDOFF_DIVIDER}\n"
        f"{row_cells}\n"
    )


def _write_supporting_artifacts(tmp_path: Path) -> tuple[Path, Path]:
    experiment_plan = tmp_path / "EXPERIMENT_PLAN.md"
    experiment_plan.write_text("# Experiment Plan\n")
    final_proposal = tmp_path / "FINAL_PROPOSAL.md"
    final_proposal.write_text("# Final Proposal\n")
    return experiment_plan, final_proposal


def test_workflow1_exit_gate_accepts_valid_ready_handoff(tmp_path: Path) -> None:
    idea_report = tmp_path / "IDEA_REPORT.md"
    experiment_plan, final_proposal = _write_supporting_artifacts(tmp_path)
    experiment_plan.write_text("# Experiment Plan\n\n## Evaluation Inputs\nready\n")
    idea_report.write_text(
        _build_idea_report(
            "| Idea 1 | 2 | IB1 verified system addresses B1/S1 | "
            "platform=[EC-P1]; workload=[EC-W1] | p99 latency | "
            "simulator_evaluation | clear | high | "
            "ready | small_local_patch | minutes_to_hours | n/a | ready | none |"
        )
    )

    result = run_tool(
        "workflow1_exit_gate.sh",
        "--idea-report",
        str(idea_report),
        "--experiment-plan",
        str(experiment_plan),
        "--final-proposal",
        str(final_proposal),
        "--selected-idea",
        "Idea 1",
    )

    assert result.returncode == 0
    assert "Workflow 1 exit gate passed" in result.stdout
    assert result.stderr == ""


def test_workflow1_exit_gate_rejects_missing_experiment_plan(tmp_path: Path) -> None:
    idea_report = tmp_path / "IDEA_REPORT.md"
    final_proposal = tmp_path / "FINAL_PROPOSAL.md"
    final_proposal.write_text("# Final Proposal\n")
    idea_report.write_text("# Research Idea Report\n")

    result = run_tool(
        "workflow1_exit_gate.sh",
        "--idea-report",
        str(idea_report),
        "--experiment-plan",
        str(tmp_path / "missing.md"),
        "--final-proposal",
        str(final_proposal),
    )

    assert result.returncode != 0
    assert "missing experiment plan" in result.stderr


def test_workflow1_exit_gate_rejects_missing_final_proposal(tmp_path: Path) -> None:
    idea_report = tmp_path / "IDEA_REPORT.md"
    experiment_plan = tmp_path / "EXPERIMENT_PLAN.md"
    idea_report.write_text("# Research Idea Report\n")
    experiment_plan.write_text("# Experiment Plan\n")

    result = run_tool(
        "workflow1_exit_gate.sh",
        "--idea-report",
        str(idea_report),
        "--experiment-plan",
        str(experiment_plan),
        "--final-proposal",
        str(tmp_path / "missing.md"),
    )

    assert result.returncode != 0
    assert "missing final proposal" in result.stderr


def test_workflow1_exit_gate_rejects_invalid_canon_ids(tmp_path: Path) -> None:
    idea_report = tmp_path / "IDEA_REPORT.md"
    experiment_plan, final_proposal = _write_supporting_artifacts(tmp_path)
    idea_report.write_text(
        _build_idea_report(
            "| Idea 1 | 2 | IB1 verified system addresses B1/S1 | "
            "platform=[GPU]; workload=[trace] | p99 latency | "
            "simulator_evaluation | clear | high | "
            "ready | small_local_patch | minutes_to_hours | n/a | ready | none |"
        )
    )

    result = run_tool(
        "workflow1_exit_gate.sh",
        "--idea-report",
        str(idea_report),
        "--experiment-plan",
        str(experiment_plan),
        "--final-proposal",
        str(final_proposal),
        "--selected-idea",
        "Idea 1",
    )

    assert result.returncode != 0
    assert "canon_mapping" in result.stderr
    assert "EC-P*" in result.stderr


def test_workflow1_exit_gate_rejects_zero_score_ready_handoff(tmp_path: Path) -> None:
    idea_report = tmp_path / "IDEA_REPORT.md"
    experiment_plan, final_proposal = _write_supporting_artifacts(tmp_path)
    idea_report.write_text(
        _build_idea_report(
            "| Idea 1 | 0 | IB1 unavailable system addresses B1 | "
            "platform=[EC-P1]; workload=[EC-W1] | p99 latency | "
            "simulator_evaluation | clear | low | "
            "ready | small_local_patch | minutes_to_hours | n/a | ready | none |"
        )
    )

    result = run_tool(
        "workflow1_exit_gate.sh",
        "--idea-report",
        str(idea_report),
        "--experiment-plan",
        str(experiment_plan),
        "--final-proposal",
        str(final_proposal),
        "--selected-idea",
        "Idea 1",
    )

    assert result.returncode != 0
    assert "baseline_evaluability_score: 0" in result.stderr


def test_workflow1_exit_gate_rejects_missing_required_field(tmp_path: Path) -> None:
    """All schema-required fields must be present and non-empty."""
    idea_report = tmp_path / "IDEA_REPORT.md"
    experiment_plan, final_proposal = _write_supporting_artifacts(tmp_path)
    # idea_adapter_cost left blank.
    idea_report.write_text(
        _build_idea_report(
            "| Idea 1 | 2 | IB1 verified system | "
            "platform=[EC-P1]; workload=[EC-W1] | p99 latency | "
            "simulator_evaluation | clear | high | "
            "ready |  | minutes_to_hours | n/a | ready | none |"
        )
    )

    result = run_tool(
        "workflow1_exit_gate.sh",
        "--idea-report",
        str(idea_report),
        "--experiment-plan",
        str(experiment_plan),
        "--final-proposal",
        str(final_proposal),
        "--selected-idea",
        "Idea 1",
    )

    assert result.returncode != 0
    assert "idea_adapter_cost" in result.stderr


def test_workflow1_exit_gate_exact_label_match_avoids_idea_10_collision(
    tmp_path: Path,
) -> None:
    """Selecting "Idea 1" must not collide with "Idea 10" / "Idea 11"."""
    idea_report = tmp_path / "IDEA_REPORT.md"
    experiment_plan, final_proposal = _write_supporting_artifacts(tmp_path)
    idea_report.write_text(
        _build_idea_report(
            "| Idea 10 | 2 | IB10 verified system | "
            "platform=[EC-P1]; workload=[EC-W1] | p99 latency | "
            "simulator_evaluation | clear | high | "
            "ready | small_local_patch | minutes_to_hours | n/a | ready | none |\n"
            "| Idea 1 | 2 | IB1 verified system | "
            "platform=[EC-P2]; workload=[EC-W2] | p99 latency | "
            "simulator_evaluation | clear | high | "
            "ready | small_local_patch | minutes_to_hours | n/a | ready | none |"
        )
    )

    result = run_tool(
        "workflow1_exit_gate.sh",
        "--idea-report",
        str(idea_report),
        "--experiment-plan",
        str(experiment_plan),
        "--final-proposal",
        str(final_proposal),
        "--selected-idea",
        "Idea 1",
    )

    assert result.returncode == 0
    assert "Workflow 1 exit gate passed: Idea 1" in result.stdout


def test_idea_report_template_carries_gate_required_columns() -> None:
    """The IDEA_REPORT_TEMPLATE handoff table must declare every schema-required field.

    Without this, the exit gate fails on a faithful copy of the template
    because the column never makes it into the rendered report.
    """
    template = read("templates/IDEA_REPORT_TEMPLATE.md")
    section_start = template.index("## Evaluation Handoff Summary")
    section = template[section_start:]
    header_line = next(
        line for line in section.splitlines() if line.startswith("| Idea")
    )
    header_columns = [cell.strip() for cell in header_line.strip("|").split("|")]

    required_columns = [
        "core_baseline",
        "canon_mapping",
        "metrics",
        "target_validation_style",
        "evaluation_target_clarity",
        "evaluation_target_feasibility",
        "evaluation_environment_access",
        "idea_adapter_cost",
        "pilot_runtime_cost",
        "baseline_evaluability_score",
        "handoff_to_workflow_1_5",
        "main_blocker",
        "negative_evidence_response",
    ]
    for column in required_columns:
        assert column in header_columns, (
            f"IDEA_REPORT_TEMPLATE.md handoff table is missing column {column!r}; "
            "downstream tools/workflow1_exit_gate.sh will fail on this template."
        )


def test_idea_templates_preserve_negative_evidence_response() -> None:
    for relative_path in [
        "templates/IDEA_REPORT_TEMPLATE.md",
        "templates/IDEA_CANDIDATES_TEMPLATE.md",
    ]:
        assert "negative_evidence_response" in read(relative_path)


def test_workflow1_consumers_preserve_negative_evidence_response() -> None:
    for relative_path in [
        "tools/workflow1_exit_gate.sh",
        "skills/experiment-plan/SKILL.md",
        "skills/experiment-bridge/SKILL.md",
        "skills/shared-references/integration-contract.md",
    ]:
        assert "negative_evidence_response" in read(relative_path)


def test_research_playbook_matches_current_workflow1_sections() -> None:
    playbook = read("docs/ARIS-Architecture-Research-Playbook.md")

    assert "Section 2.5" in playbook
    assert "Negative Evidence" in playbook
    assert "NE-*" in playbook
    assert "Section 4 `Landscape Pack`" in playbook
    assert "Section 5 `Landscape Pack`" not in playbook
    assert "Section 5 Landscape Pack" not in playbook
    assert "Section 4 `Competitive Landscape`" not in playbook
