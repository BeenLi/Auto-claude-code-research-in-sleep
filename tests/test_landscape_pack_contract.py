from __future__ import annotations

import re
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def read(relative_path: str) -> str:
    return (REPO_ROOT / relative_path).read_text()


def table_columns(row: str) -> list[str]:
    stripped = row.strip()
    if not stripped.startswith("|") or not stripped.endswith("|"):
        return []
    return [cell.strip() for cell in stripped.strip("|").split("|")]


def landscape_pack_contract(text: str) -> str:
    marker = "## Landscape Pack Contract"
    start = text.index(marker)
    end = text.index("## Key Rules", start)
    return text[start:end]


def landscape_pack_markdown_block(text: str) -> str:
    contract = landscape_pack_contract(text)
    fence_open = contract.index("```markdown")
    fence_open = contract.index("\n", fence_open) + 1
    fence_close = contract.index("```", fence_open)
    return contract[fence_open:fence_close]


def assert_table_shape(markdown: str) -> None:
    rows = [line for line in markdown.splitlines() if line.strip().startswith("|")]
    for header, separator in zip(rows, rows[1:]):
        separator_cells = table_columns(separator)
        if separator_cells and all(re.fullmatch(r":?-{3,}:?", cell) for cell in separator_cells):
            header_cells = table_columns(header)
            assert len(header_cells) == len(separator_cells), header
            assert len(header_cells) <= 7, header


def test_research_lit_landscape_pack_contract_uses_revised_schema() -> None:
    contract = landscape_pack_contract(read("skills/research-lit/SKILL.md"))

    required_fragments = [
        "### Topic Scope",
        "### Bottleneck Evidence",
        "#### Bottlenecks",
        "| bottleneck_id | bottleneck | context | decisive_metrics | representative_papers | current_status | residual_gap |",
        "#### Solution Attempts",
        "| solution_id | bottleneck_ids | mechanism_family | representative_papers | best_outcome | missing_piece |",
        "### Evaluation Canon",
        "#### Platforms",
        "| platform_id | evaluation_platform | access_readiness | supported_workloads | validates_refs | artifact_access_path | platform_limitations |",
        "#### Workloads",
        "| workload_id | workload | bottlenecks | workload_characteristics | representative_papers | representativeness_limits |",
        "### Gap Seeds",
        "| gap_id | bottleneck_id | source_gap_ref | mechanism_hint | validation_target | decisive_metric | kill_reason |",
    ]

    for fragment in required_fragments:
        assert fragment in contract

    forbidden_fragments = [
        "### Core Baseline Candidates",
        "### Simulator / Prototype Readiness",
        "| baseline_id | paper_or_system | addresses | canon_mapping | metrics | artifact_status |",
        "| backend | platform_id | readiness | validates | blocker |",
        "| platform_id | platform_or_backend | backend_readiness | workloads | validates | artifact_access_path | blockers_or_limitations |",
        "| workload_id | workload | bottlenecks | metrics | representative_papers | limitations |",
        "| gap_id | bottleneck_id | source_residual | mechanism_hint | validation_target | decisive_metric | kill_reason |",
        "platform_or_backend",
        "backend_readiness",
        "blockers_or_limitations",
        "`Workloads.metrics`",
    ]
    for fragment in forbidden_fragments:
        assert fragment not in contract

    assert "### Mechanism Clusters" not in contract
    assert "| canon_id | category | item |" not in contract
    assert "| gap_id | gap_type |" not in contract
    assert_table_shape(landscape_pack_markdown_block(read("skills/research-lit/SKILL.md")))


def test_research_lit_contract_declares_reference_resolution_rules() -> None:
    contract = landscape_pack_contract(read("skills/research-lit/SKILL.md"))
    contract_flat = re.sub(r"\s+", " ", contract)

    required_rules = [
        "`S*.bottleneck_ids` is a comma-separated list of `B*` IDs",
        "Every entry must resolve to a `B*`.",
        "`evaluation_platform` is the concrete evaluation substrate",
        "`access_readiness` is one of `ready`, `small_adapter_needed`, `major_bringup_needed`, `unavailable`, `unknown`.",
        "`validates_refs` entries must resolve to `B*` or `S*`.",
        "`platform_limitations` records platform, access, or fidelity blockers",
        "`workload_characteristics` records workload shape",
        "`representativeness_limits` records workload-level caveats",
        "Every `EC-W*.bottlenecks` entry must resolve to `B*`.",
        "Every `G*.bottleneck_id` must resolve to `B*`.",
        "Every `G*.source_gap_ref` must point to `B*.residual_gap`, `S*.missing_piece`, or explicit negative evidence.",
        "`Bottlenecks.residual_gap` records the unresolved problem; `Gap Seeds` converts one or more residuals into an actionable idea seed",
        "No Landscape Pack table should exceed 7 columns.",
    ]

    for rule in required_rules:
        assert rule in contract_flat


def test_downstream_skill_wording_matches_nested_landscape_pack() -> None:
    idea_creator = read("skills/idea-creator/SKILL.md")
    idea_discovery = read("skills/idea-discovery/SKILL.md")

    assert "`Bottleneck Evidence` contains `Bottlenecks` and `Solution Attempts`" in idea_creator
    assert "`Evaluation Canon` contains `Platforms` and `Workloads`" in idea_creator
    assert "evaluation_platform" in idea_creator
    assert "access_readiness" in idea_creator
    assert "validates_refs" in idea_creator
    assert "platform_limitations" in idea_creator
    assert "workload_characteristics" in idea_creator
    assert "representativeness_limits" in idea_creator
    assert "workload-level metrics" not in idea_creator
    assert "Solution Attempts" in idea_creator
    assert "Mechanism Clusters" not in idea_creator
    assert "category=evaluation_platform" not in idea_creator
    assert "category=benchmark_workload" not in idea_creator
    assert "item-level Evaluation Canon rows: evaluation_platform and benchmark_workload" not in idea_creator
    assert "Core Baseline Candidates" not in idea_creator
    assert "Simulator / Prototype Readiness" not in idea_creator
    assert "idea-local baseline record" in idea_creator
    assert "baseline_evaluability_score" in idea_creator

    assert "Bottleneck Evidence: B* bottlenecks and S* solution attempts" in idea_discovery
    assert "Evaluation Canon: platforms=[EC-P* evaluation_platform/access_readiness summary], workloads=[EC-W* workload_characteristics summary]" in idea_discovery
    assert "Idea-local baselines: derived per idea" in idea_discovery
    assert "Gap Seeds: [top G* residual-gap seeds]" in idea_discovery
    assert "workload-level metrics" not in idea_discovery


def test_research_pipeline_still_preserves_handoff_contract_ids() -> None:
    research_pipeline = read("skills/research-pipeline/SKILL.md")
    schema = read("skills/shared-references/idea-handoff-schema.md")

    assert "../shared-references/idea-handoff-schema.md" in research_pipeline
    assert "tools/workflow1_exit_gate.sh" in research_pipeline
    assert "`core_baseline`" in schema
    assert "`baseline_evaluability_score: 0` cannot be `handoff_to_workflow_1_5: ready`" in schema
    assert "The platform ID must reference `EC-P*`" in schema
    assert "the workload ID must reference `EC-W*`" in schema


def test_mock_landscape_pack_reference_rules_resolve() -> None:
    mock_pack = {
        "bottlenecks": {"B1", "B2"},
        "solutions": {"S1": ["B1", "B2"]},
        "platforms": {"EC-P1": ["B1", "S1"]},
        "workloads": {"EC-W1": ["B1"]},
        "gaps": {
            "G1": {
                "bottleneck_id": "B1",
                "source_gap_ref": "S1.missing_piece",
            }
        },
    }

    bottlenecks = mock_pack["bottlenecks"]
    solutions = mock_pack["solutions"]
    platforms = mock_pack["platforms"]
    workloads = mock_pack["workloads"]

    assert all(
        all(bid in bottlenecks for bid in bids) for bids in solutions.values()
    )

    for validates in platforms.values():
        for item in validates:
            assert item in bottlenecks or item in solutions

    for characterized in workloads.values():
        for item in characterized:
            assert item in bottlenecks

    for gap in mock_pack["gaps"].values():
        assert gap["bottleneck_id"] in bottlenecks
        source_id, source_field = gap["source_gap_ref"].split(".")
        assert (source_id in bottlenecks and source_field == "residual_gap") or (
            source_id in solutions and source_field == "missing_piece"
        )


def test_research_lit_declares_mandatory_paper_verification_gate() -> None:
    text = read("skills/research-lit/SKILL.md")
    reference = read("skills/research-lit/references/verify-candidate-papers.md")

    main_fragments = [
        "### 2.5. Verify Candidate Papers",
        "references/verify-candidate-papers.md",
        ".aris/verify-papers/candidate_papers.json",
        ".aris/verify-papers/verified_papers.json",
        "`BLOCKED` prevents saving the literature review",
        "`WARN` continues with degraded output",
    ]
    for fragment in main_fragments:
        assert fragment in text

    reference_fragments = [
        ".aris/tools/verify_papers.py",
        "tools/verify_papers.py",
        "$ARIS_REPO/tools/verify_papers.py",
        ".aris/verify-papers/candidate_papers.json",
        ".aris/verify-papers/verified_papers.json",
        "`verified`, `unverified`, `verify_pending`, and `error`",
        "`PASS`, `WARN`, `BLOCKED`, and `ERROR`",
        "`BLOCKED` prevents saving the literature review",
        "`WARN` continues with degraded output",
        "zero verified papers",
        "command -v python3",
        "verifier_missing",
    ]
    for fragment in reference_fragments:
        assert fragment in reference

    assert "command -v python3" not in text
    assert "verifier_missing" not in text

    assert "| Paper | Venue | Year | Method | Key Result | Eval Platform | Workload | Baseline | Relevance | Source | Verification | Preprint | Full Text | Artifact |" in text


def test_idea_creator_requires_idea_local_verified_baselines() -> None:
    idea_creator = read("skills/idea-creator/SKILL.md")
    schema = read("skills/shared-references/idea-handoff-schema.md")

    required_fragments = [
        "idea-local baseline record",
        "baseline_id",
        "paper_or_system",
        "verification_status",
        "addresses",
        "canon_mapping",
        "metrics",
        "artifact_status",
        "baseline_reproducibility",
        "baseline_evaluability_score",
        "`2` = official/open-source/config reproducible",
        "`1` = paper-only or unknown",
        "`0` = proprietary/unavailable or unverified-only",
        "`baseline_evaluability_score: 0` cannot be `handoff_to_workflow_1_5: ready`",
    ]
    for fragment in required_fragments:
        assert fragment in schema

    assert "../shared-references/idea-handoff-schema.md" in idea_creator
