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


def test_playbook_overview_uses_public_refine_pipeline_wrapper() -> None:
    playbook = read("docs/ARIS-Architecture-Research-Playbook.md")
    overview = playbook[: playbook.index("**Workflow 1.5")]

    assert (
        "`research-lit` -> `idea-creator` -> `novelty-check` -> "
        "`research-review` -> `research-refine-pipeline`"
    ) in overview
    assert "`research-refine` -> `experiment-plan`" not in overview


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


def test_workflow1_guidance_drops_fixed_batch_handoff_constants() -> None:
    workflow1_guidance = "\n".join(
        [
            read("README.md"),
            read("skills/idea-discovery/SKILL.md"),
            read("skills/skills-codex/idea-discovery/SKILL.md"),
            read("docs/ARIS-Architecture-Research-Playbook.md"),
        ]
    )

    forbidden_fragments = [
        "MAX_HANDOFF_IDEAS",
        "MAX\\_HANDOFF\\_IDEAS",
        "MAX_READY_FOR_WORKFLOW_1_5",
        "MAX\\_READY\\_FOR\\_WORKFLOW\\_1\\_5",
        "at most 6 strong ideas",
        "at most 3 ideas as immediate Workflow 1.5 candidates",
        "Mark at most 3 ideas as immediate Workflow 1.5 candidates",
    ]
    for fragment in forbidden_fragments:
        assert fragment not in workflow1_guidance

    assert "priority-ordered" in workflow1_guidance
    assert "single-selected" in workflow1_guidance


def test_handoff_schema_is_single_shared_reference() -> None:
    schema = read("skills/shared-references/idea-handoff-schema.md")
    required_fields = [
        "core_baseline",
        "baseline_artifact_readiness",
        "canon_mapping",
        "metrics",
        "target_validation_style",
        "evaluation_target_clarity",
        "evaluation_feasibility_score",
        "evaluation_feasibility_breakdown",
        "refine_overall_score",
        "refine_verdict",
        "drift_status",
        "handoff_refresh_status",
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


def test_handoff_schema_keeps_summary_fields_and_merges_subfields() -> None:
    schema = read("skills/shared-references/idea-handoff-schema.md")
    template = read("templates/IDEA_REPORT_TEMPLATE.md")
    integration_contract = read("skills/shared-references/integration-contract.md")

    required_fragments = [
        "The handoff keeps `baseline_artifact_readiness` and `evaluation_feasibility_score` as the merged gate fields.",
        '"Baseline" (code availability) is strictly separate from "Platform/Workload Access"',
        "`baseline_artifact_readiness.score` carries the baseline gate",
        "`evaluation_feasibility_score` carries the environment, adapter, and runtime readiness gate",
        "`evaluation_feasibility_breakdown` records `platform_workload_access`, `evaluation_adapter_cost`, and `first_signal_runtime` while referencing `baseline_artifact_readiness` for the baseline dimension.",
    ]
    for fragment in required_fragments:
        assert fragment in schema

    required_template_fields = [
        "baseline_artifact_readiness",
        "evaluation_feasibility_score",
        "evaluation_feasibility_breakdown",
    ]
    for field in required_template_fields:
        assert field in template

    assert "`evaluation_feasibility_score`" in integration_contract
    assert "`baseline_verification_delta`" in integration_contract
    assert "feasibility fields" not in integration_contract

    forbidden_template_fields = [
        "baseline_code_availability_score",
        "baseline_reproducibility",
        "evaluation_environment_access",
        "idea_adapter_cost",
        "pilot_runtime_cost",
    ]
    for field in forbidden_template_fields:
        assert field not in template


def test_evaluation_canon_is_defined_as_platform_and_workload_ids_only() -> None:
    schema = read("skills/shared-references/idea-handoff-schema.md")
    idea_creator = read("skills/idea-creator/SKILL.md")
    idea_creator_mirror = read("skills/skills-codex/idea-creator/SKILL.md")
    experiment_bridge = read("skills/experiment-bridge/SKILL.md")
    experiment_plan = read("skills/experiment-plan/SKILL.md")
    research_pipeline = read("skills/research-pipeline/SKILL.md")
    combined = "\n".join(
        [
            schema,
            idea_creator,
            idea_creator_mirror,
            experiment_bridge,
            experiment_plan,
            research_pipeline,
        ]
    )

    required_definition_fragments = [
        "In this workflow, `Evaluation Canon` means only the literature-derived platform and workload reference set",
        "`EC-P*` platform rows",
        "`EC-W*` workload rows",
        "`canon_mapping` is only `platform=[EC-P*]; workload=[EC-W*]`",
        "Baselines, metrics, validation style, feasibility, and clarity are not canon",
    ]
    for fragment in required_definition_fragments:
        assert fragment in schema

    required_usage_fragments = [
        "Use the Evaluation Canon only as provenance for platform/workload choices.",
        "Populate the handoff fields from `../shared-references/idea-handoff-schema.md`.",
        "Select an evaluation backend from `core_baseline` plus the platform/workload IDs in `canon_mapping`.",
        "selected evaluation backend follows the baseline and platform/workload mapping",
    ]
    for fragment in required_usage_fragments:
        assert fragment in combined

    forbidden_misuse_fragments = [
        "evidence canon",
        "canonical baseline, canon, metrics, validation-style, and clarity fields",
        "baseline/canon mapping",
        "selected evaluation backend follows the baseline/canon mapping",
        "core_baseline` and `canon_mapping`",
    ]
    for fragment in forbidden_misuse_fragments:
        assert fragment not in combined


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


def test_idea_creator_derives_domain_context_from_literature_review() -> None:
    idea_creator = read("skills/idea-creator/SKILL.md")

    forbidden_fixed_scope = [
        "AI Infrastructure Layer Taxonomy",
        "Domain context: AI infrastructure for LLM",
        "The problem must be an LLM / AI infrastructure problem",
        "The problem must fit the literature-derived topic scope.",
        "The idea must name a concrete architecture, systems, measurement, benchmark, trace/workload, or mechanism question.",
        "Hard gates:",
        "Default weighted score after hard gates:",
        "Apply hard gates from the rubric",
        "selected AI infrastructure topic",
        "Diverse across AI infrastructure layers",
        "AI infrastructure hardware",
        "Reject ideas outside the literature-derived topic scope.",
        "Reject ideas without a concrete architecture, systems, measurement, benchmark, trace/workload, or mechanism question.",
    ]
    for phrase in forbidden_fixed_scope:
        assert phrase not in idea_creator

    required_dynamic_scope = [
        "derive the domain context from `idea-stage/LITERATURE_REVIEW.md`",
        "Do not inject a repository-wide domain default",
        "Topic Scope",
        "Domain context: [paste Topic Scope from /research-lit Section 4]",
    ]
    for phrase in required_dynamic_scope:
        assert phrase in idea_creator


def test_idea_creator_verifies_only_new_baseline_candidates_and_logs_delta() -> None:
    idea_creator = read("skills/idea-creator/SKILL.md")
    schema = read("skills/shared-references/idea-handoff-schema.md")
    template = read("templates/IDEA_REPORT_TEMPLATE.md")

    required_fragments = [
        "Do not re-run `verify_papers.py` for Section 1 or Section 4 evidence already verified by `/research-lit`.",
        "only when `idea-creator` adds a new baseline candidate",
        "announce the lookup to the user",
        "baseline_verification_delta",
        "new_baseline_lookup",
        "verified_by_research_lit",
    ]
    for fragment in required_fragments:
        assert fragment in idea_creator

    assert "baseline_verification_delta" in schema
    assert "baseline_verification_delta" in template


def test_idea_creator_handoff_planning_is_priority_ordered_not_fixed_batch() -> None:
    idea_creator = read("skills/idea-creator/SKILL.md")
    idea_creator_mirror = read("skills/skills-codex/idea-creator/SKILL.md")
    idea_discovery = read("skills/idea-discovery/SKILL.md")
    idea_discovery_mirror = read("skills/skills-codex/idea-discovery/SKILL.md")
    playbook = read("docs/ARIS-Architecture-Research-Playbook.md")
    combined_idea_creator = "\n".join([idea_creator, idea_creator_mirror])
    workflow1_guidance = "\n".join(
        [idea_creator, idea_creator_mirror, idea_discovery, idea_discovery_mirror, playbook]
    )

    forbidden_batch_fragments = [
        "top 4-6",
        "Top 4-6",
        "Select top 4-6 ideas",
        "For each top 4-6 idea",
        "Typically 8-12 ideas reduce to 4-6",
        "MAX_HANDOFF_IDEAS",
        "MAX_READY_FOR_WORKFLOW_1_5",
        "2-3 immediate Workflow 1.5 candidates",
    ]
    for phrase in forbidden_batch_fragments:
        assert phrase not in workflow1_guidance

    forbidden_handoff_constant_fragments = [
        "PRIMARY_HANDOFF_ATTEMPT",
        "BACKUP_HANDOFF_ATTEMPTS",
    ]
    for phrase in forbidden_handoff_constant_fragments:
        assert phrase not in combined_idea_creator

    required_priority_fragments = [
        "### Phase 5: Evaluation Handoff Planning (priority-ordered ideas)",
        "Start with the highest-ranked surviving idea.",
        "If the highest-ranked idea cannot reach a reproducible baseline path",
        "record the failed handoff attempt",
        "then try the next ranked surviving idea.",
    ]
    for phrase in required_priority_fragments:
        assert phrase in idea_creator


def test_overall_merit_score_uses_high_is_better_scale() -> None:
    idea_creator = read("skills/idea-creator/SKILL.md")
    combined = "\n".join(
        [
            idea_creator,
            read("skills/skills-codex/idea-creator/SKILL.md"),
            read("skills/idea-discovery/SKILL.md"),
            read("skills/research-pipeline/SKILL.md"),
            read("templates/IDEA_REPORT_TEMPLATE.md"),
            read("templates/IDEA_CANDIDATES_TEMPLATE.md"),
        ]
    )

    required_fragments = [
        "`overall_merit_score` follows a target-venue reviewer scale where 5 is best and 1 is worst:",
        "`5`: Surprisingly new contribution, or likely to have major impact on future research/products; may inspire new research or start a new line.",
        "`4`: Clear new contribution, or likely to impact future research/products.",
        "`3`: Incremental but valid improvement, with limited yet non-trivial impact.",
        "`2`: Weak novelty or marginal impact; generally not enough to justify acceptance.",
        "`1`: No clear novelty, or unlikely to have meaningful impact; should be rejected.",
        "Assign `overall_merit_score: 1 | 2 | 3 | 4 | 5` using the reviewer-style scale above.",
        "Rank surviving ideas with `overall_merit_score` 60% and `evaluation_feasibility_score` 40%.",
    ]
    for fragment in required_fragments:
        assert fragment in idea_creator

    forbidden_fragments = [
        "1 is best and 4 is worst",
        "overall_merit_points",
        "overall_merit_points = 5 - overall_merit_score",
        "Assign `overall_merit_score: 1 | 2 | 3 | 4`",
        "score 4; differentiated and impactful ideas may score 1 or 2",
        "Eliminate `overall_merit_score: 4` ideas",
        "overall_merit_score: 1-3",
        "[1-4]",
        "1->2, 2->3",
    ]
    for fragment in forbidden_fragments:
        assert fragment not in combined

    assert "5->4, 4->3, 3->2" in combined


def test_evaluation_feasibility_score_uses_high_is_better_scale() -> None:
    schema = read("skills/shared-references/idea-handoff-schema.md")
    idea_creator = read("skills/idea-creator/SKILL.md")
    idea_creator_mirror = read("skills/skills-codex/idea-creator/SKILL.md")
    exit_gate = read("tools/workflow1_exit_gate.sh")
    combined = "\n".join([schema, idea_creator, idea_creator_mirror, exit_gate])

    required_fragments = [
        "`evaluation_feasibility_score` | `1` \\| `2` \\| `3` \\| `4` \\| `5`",
        "`5` = ready evaluation path",
        "`1` = no credible evaluation path",
        "ready handoff requires `evaluation_feasibility_score` 4 or 5",
        "Rank surviving ideas with `overall_merit_score` 60% and `evaluation_feasibility_score` 40%.",
    ]
    for fragment in required_fragments:
        assert fragment in combined

    forbidden_fragments = [
        "is high or medium for a ready handoff",
        "must be high or medium for ready handoff",
        "low/unknown cannot be ready",
        "`high` \\| `medium` \\| `low` \\| `unknown`",
        "evaluation_feasibility_points",
    ]
    for fragment in forbidden_fragments:
        assert fragment not in combined


def test_workflow1_docs_use_current_evaluation_feasibility_contract() -> None:
    docs = "\n".join(
        [
            read("skills/idea-discovery/SKILL.md"),
            read("skills/skills-codex/idea-discovery/SKILL.md"),
            read("docs/ARIS-Architecture-Research-Playbook.md"),
        ]
    )

    required_fragments = [
        "evaluation_feasibility_score",
        "priority-ordered",
    ]
    for fragment in required_fragments:
        assert fragment in docs

    forbidden_fragments = [
        "evaluation target feasibility",
        "feasibility fields, platform path",
        "baseline reproducibility, environment access, adapter cost, pilot runtime cost",
        "environment access, adapter cost, pilot runtime cost",
        "Select the evaluation backend from `core_baseline` and `canon_mapping`",
    ]
    for fragment in forbidden_fragments:
        assert fragment not in docs


def test_research_pipeline_requires_explicit_brief_path() -> None:
    stage1 = research_pipeline_stage1()

    assert "RESEARCH_BRIEF.md" in stage1
    assert "explicit" in stage1
    assert "automatically loaded" not in stage1
    assert "If `RESEARCH_BRIEF.md` exists in the project root" not in stage1


def test_research_pipeline_exit_gate_example_passes_all_required_artifacts() -> None:
    research_pipeline = read("skills/research-pipeline/SKILL.md")

    assert (
        "tools/workflow1_exit_gate.sh --idea-report idea-stage/IDEA_REPORT.md "
        "--experiment-plan refine-logs/EXPERIMENT_PLAN.md "
        "--final-proposal refine-logs/FINAL_PROPOSAL.md "
        "--selected-idea"
    ) in research_pipeline


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
    "| Idea | baseline_artifact_readiness | core_baseline | canon_mapping | metrics | "
    "target_validation_style | evaluation_target_clarity | evaluation_feasibility_score | "
    "evaluation_feasibility_breakdown | baseline_verification_delta | negative_evidence_response | "
    "refine_overall_score | refine_verdict | drift_status | handoff_refresh_status | "
    "handoff_to_workflow_1_5 | main_blocker |"
)
READY_HANDOFF_DIVIDER = (
    "|------|-----------------------------|---------------|---------------|---------|"
    "-------------------------|---------------------------|-------------------------------|"
    "--------------------------------|-----------------------------|----------------------------|"
    "----------------------|----------------|--------------|------------------------|"
    "-------------------------|--------------|"
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


VALID_BASELINE_READINESS = "score=2; status=official_artifact; verification=verified"
LOW_BASELINE_READINESS = "score=0; status=proprietary_or_unavailable; verification=unverified"
VALID_FEASIBILITY_BREAKDOWN = (
    "platform_workload_access=ready; evaluation_adapter_cost=small; "
    "first_signal_runtime=hours"
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
            f"| Idea 1 | {VALID_BASELINE_READINESS} | IB1 verified system addresses B1/S1 | "
            "platform=[EC-P1]; workload=[EC-W1] | p99 latency | "
            f"simulator_evaluation | clear | 5 | {VALID_FEASIBILITY_BREAKDOWN} | "
            "verified_by_research_lit | n/a | 9 | READY | preserved | passed | ready | none |"
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
            f"| Idea 1 | {VALID_BASELINE_READINESS} | IB1 verified system addresses B1/S1 | "
            "platform=[GPU]; workload=[trace] | p99 latency | "
            f"simulator_evaluation | clear | 5 | {VALID_FEASIBILITY_BREAKDOWN} | "
            "verified_by_research_lit | n/a | 9 | READY | preserved | passed | ready | none |"
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
            f"| Idea 1 | {LOW_BASELINE_READINESS} | IB1 unavailable system addresses B1 | "
            "platform=[EC-P1]; workload=[EC-W1] | p99 latency | "
            f"simulator_evaluation | clear | 2 | {VALID_FEASIBILITY_BREAKDOWN} | "
            "verification_unresolved | n/a | 9 | READY | preserved | passed | ready | none |"
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
    assert "baseline_artifact_readiness.score: 0" in result.stderr


def test_workflow1_exit_gate_rejects_low_feasibility_score_ready_handoff(tmp_path: Path) -> None:
    idea_report = tmp_path / "IDEA_REPORT.md"
    experiment_plan, final_proposal = _write_supporting_artifacts(tmp_path)
    idea_report.write_text(
        _build_idea_report(
            f"| Idea 1 | {VALID_BASELINE_READINESS} | IB1 verified system addresses B1 | "
            "platform=[EC-P1]; workload=[EC-W1] | p99 latency | "
            f"simulator_evaluation | clear | 2 | {VALID_FEASIBILITY_BREAKDOWN} | "
            "verified_by_research_lit | n/a | 9 | READY | preserved | passed | ready | none |"
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
    assert "evaluation_feasibility_score" in result.stderr


def test_workflow1_exit_gate_rejects_missing_required_field(tmp_path: Path) -> None:
    """All schema-required fields must be present and non-empty."""
    idea_report = tmp_path / "IDEA_REPORT.md"
    experiment_plan, final_proposal = _write_supporting_artifacts(tmp_path)
    # metrics left blank.
    idea_report.write_text(
        _build_idea_report(
            f"| Idea 1 | {VALID_BASELINE_READINESS} | IB1 verified system | "
            "platform=[EC-P1]; workload=[EC-W1] |  | "
            f"simulator_evaluation | clear | 5 | {VALID_FEASIBILITY_BREAKDOWN} | "
            "verified_by_research_lit | n/a | 9 | READY | preserved | passed | ready | none |"
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
    assert "metrics" in result.stderr


def test_workflow1_exit_gate_exact_label_match_avoids_idea_10_collision(
    tmp_path: Path,
) -> None:
    """Selecting "Idea 1" must not collide with "Idea 10" / "Idea 11"."""
    idea_report = tmp_path / "IDEA_REPORT.md"
    experiment_plan, final_proposal = _write_supporting_artifacts(tmp_path)
    idea_report.write_text(
        _build_idea_report(
            f"| Idea 10 | {VALID_BASELINE_READINESS} | IB10 verified system | "
            "platform=[EC-P1]; workload=[EC-W1] | p99 latency | "
            f"simulator_evaluation | clear | 5 | {VALID_FEASIBILITY_BREAKDOWN} | "
            "verified_by_research_lit | n/a | 9 | READY | preserved | passed | ready | none |\n"
            f"| Idea 1 | {VALID_BASELINE_READINESS} | IB1 verified system | "
            "platform=[EC-P2]; workload=[EC-W2] | p99 latency | "
            f"simulator_evaluation | clear | 5 | {VALID_FEASIBILITY_BREAKDOWN} | "
            "verified_by_research_lit | n/a | 9 | READY | preserved | passed | ready | none |"
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


def test_workflow1_exit_gate_accepts_feasibility_score_with_rationale(
    tmp_path: Path,
) -> None:
    idea_report = tmp_path / "IDEA_REPORT.md"
    experiment_plan, final_proposal = _write_supporting_artifacts(tmp_path)
    idea_report.write_text(
        _build_idea_report(
            f"| Idea 1 | {VALID_BASELINE_READINESS} | IB1 verified system addresses B1/S1 | "
            "platform=[EC-P1]; workload=[EC-W1] | p99 latency | "
            "simulator_evaluation | clear | 5 -- ready platform, minutes-to-hours first signal | "
            f"{VALID_FEASIBILITY_BREAKDOWN} | verified_by_research_lit | n/a | "
            "9 | READY | preserved | passed | ready | none |"
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


def test_workflow1_exit_gate_rejects_missing_baseline_verification_delta(
    tmp_path: Path,
) -> None:
    idea_report = tmp_path / "IDEA_REPORT.md"
    experiment_plan, final_proposal = _write_supporting_artifacts(tmp_path)
    idea_report.write_text(
        "# Research Idea Report\n\n"
        "## Evaluation Handoff Summary\n"
        "| Idea | baseline_artifact_readiness | core_baseline | canon_mapping | metrics | "
        "target_validation_style | evaluation_target_clarity | evaluation_feasibility_score | "
        "evaluation_feasibility_breakdown | negative_evidence_response | "
        "refine_overall_score | refine_verdict | drift_status | handoff_refresh_status | "
        "handoff_to_workflow_1_5 | main_blocker |\n"
        "|------|-----------------------------|---------------|---------------|---------|"
        "-------------------------|---------------------------|-------------------------------|"
        "--------------------------------|----------------------------|----------------------|"
        "----------------|--------------|------------------------|-------------------------|--------------|\n"
        f"| Idea 1 | {VALID_BASELINE_READINESS} | IB1 verified system addresses B1/S1 | "
        "platform=[EC-P1]; workload=[EC-W1] | p99 latency | "
        f"simulator_evaluation | clear | 5 | {VALID_FEASIBILITY_BREAKDOWN} | "
        "n/a | 9 | READY | preserved | passed | ready | none |\n"
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
    assert "baseline_verification_delta" in result.stderr


def test_workflow1_exit_gate_reports_missing_baseline_score_column(
    tmp_path: Path,
) -> None:
    idea_report = tmp_path / "IDEA_REPORT.md"
    experiment_plan, final_proposal = _write_supporting_artifacts(tmp_path)
    idea_report.write_text(
        "# Research Idea Report\n\n"
        "## Evaluation Handoff Summary\n"
        "| Idea | core_baseline | canon_mapping | metrics | "
        "target_validation_style | evaluation_target_clarity | evaluation_feasibility_score | "
        "evaluation_feasibility_breakdown | baseline_verification_delta | negative_evidence_response | "
        "refine_overall_score | refine_verdict | drift_status | handoff_refresh_status | "
        "handoff_to_workflow_1_5 | main_blocker |\n"
        "|------|---------------|---------------|---------|"
        "-------------------------|---------------------------|-------------------------------|"
        "--------------------------------|-----------------------------|----------------------------|"
        "----------------------|----------------|--------------|------------------------|"
        "-------------------------|--------------|\n"
        "| Idea 1 | IB1 verified system addresses B1/S1 | "
        "platform=[EC-P1]; workload=[EC-W1] | p99 latency | "
        f"simulator_evaluation | clear | 5 | {VALID_FEASIBILITY_BREAKDOWN} | "
        "verified_by_research_lit | n/a | 9 | READY | preserved | passed | ready | none |\n"
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
    assert (
        "handoff table is missing required column: baseline_artifact_readiness"
        in result.stderr
    )


def test_workflow1_exit_gate_rejects_non_ready_refine_verdict(tmp_path: Path) -> None:
    idea_report = tmp_path / "IDEA_REPORT.md"
    experiment_plan, final_proposal = _write_supporting_artifacts(tmp_path)
    idea_report.write_text(
        _build_idea_report(
            f"| Idea 1 | {VALID_BASELINE_READINESS} | IB1 verified system addresses B1/S1 | "
            "platform=[EC-P1]; workload=[EC-W1] | p99 latency | "
            f"simulator_evaluation | clear | 5 | {VALID_FEASIBILITY_BREAKDOWN} | "
            "verified_by_research_lit | n/a | 8 | REVISE | preserved | passed | ready | none |"
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
    assert "refine_verdict" in result.stderr


def test_workflow1_exit_gate_rejects_drifted_refine_status(tmp_path: Path) -> None:
    idea_report = tmp_path / "IDEA_REPORT.md"
    experiment_plan, final_proposal = _write_supporting_artifacts(tmp_path)
    idea_report.write_text(
        _build_idea_report(
            f"| Idea 1 | {VALID_BASELINE_READINESS} | IB1 verified system addresses B1/S1 | "
            "platform=[EC-P1]; workload=[EC-W1] | p99 latency | "
            f"simulator_evaluation | clear | 5 | {VALID_FEASIBILITY_BREAKDOWN} | "
            "verified_by_research_lit | n/a | 9 | READY | drifted | passed | ready | none |"
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
    assert "drift_status" in result.stderr


def test_workflow1_exit_gate_rejects_missing_handoff_refresh(tmp_path: Path) -> None:
    idea_report = tmp_path / "IDEA_REPORT.md"
    experiment_plan, final_proposal = _write_supporting_artifacts(tmp_path)
    idea_report.write_text(
        _build_idea_report(
            f"| Idea 1 | {VALID_BASELINE_READINESS} | IB1 verified system addresses B1/S1 | "
            "platform=[EC-P1]; workload=[EC-W1] | p99 latency | "
            f"simulator_evaluation | clear | 5 | {VALID_FEASIBILITY_BREAKDOWN} | "
            "verified_by_research_lit | n/a | 9 | READY | preserved | not_run | ready | none |"
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
    assert "handoff_refresh_status" in result.stderr


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
        "evaluation_feasibility_score",
        "evaluation_feasibility_breakdown",
        "baseline_artifact_readiness",
        "baseline_verification_delta",
        "refine_overall_score",
        "refine_verdict",
        "drift_status",
        "handoff_refresh_status",
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
