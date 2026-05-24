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
        "| platform_id | platform | readiness | workloads | validates | artifacts | limitations |",
        "#### Workloads",
        "| workload_id | workload | bottlenecks | metrics | representative_papers | limitations |",
        "### Core Baseline Candidates",
        "| baseline_id | paper_or_system | addresses | canon_mapping | metrics | artifact_status |",
        "### Simulator / Prototype Readiness",
        "| backend | platform_id | readiness | validates | blocker |",
        "### Gap Seeds",
        "| gap_id | bottleneck_id | source_residual | mechanism_hint | validation_target | decisive_metric | kill_reason |",
    ]

    for fragment in required_fragments:
        assert fragment in contract

    assert "### Mechanism Clusters" not in contract
    assert "| canon_id | category | item |" not in contract
    assert "| gap_id | gap_type |" not in contract
    assert_table_shape(landscape_pack_markdown_block(read("skills/research-lit/SKILL.md")))


def test_research_lit_contract_declares_reference_resolution_rules() -> None:
    contract = landscape_pack_contract(read("skills/research-lit/SKILL.md"))

    required_rules = [
        "`S*.bottleneck_ids` is a comma-separated list of `B*` IDs",
        "Every entry must resolve to a `B*`.",
        "Every `CB*.addresses` must reference a valid `B*`, `S*`, or `none_found`.",
        "Every `CB*.canon_mapping` must use `platform=[EC-P*]; workload=[EC-W*]`, or explicit `none_found`.",
        "Every `EC-P*.validates` entry must resolve to `B*` or `S*`.",
        "Every `EC-W*.bottlenecks` entry must resolve to `B*`.",
        "Every `G*.bottleneck_id` must resolve to `B*`.",
        "Every `G*.source_residual` must point to `B*.residual_gap`, `S*.missing_piece`, or explicit negative evidence.",
        "No Landscape Pack table should exceed 7 columns.",
    ]

    for rule in required_rules:
        assert rule in contract


def test_downstream_skill_wording_matches_nested_landscape_pack() -> None:
    idea_creator = read("skills/idea-creator/SKILL.md")
    idea_discovery = read("skills/idea-discovery/SKILL.md")

    assert "`Bottleneck Evidence` contains `Bottlenecks` and `Solution Attempts`" in idea_creator
    assert "`Evaluation Canon` contains `Platforms` and `Workloads`" in idea_creator
    assert "Solution Attempts" in idea_creator
    assert "Mechanism Clusters" not in idea_creator
    assert "category=evaluation_platform" not in idea_creator
    assert "category=benchmark_workload" not in idea_creator
    assert "item-level Evaluation Canon rows: evaluation_platform and benchmark_workload" not in idea_creator

    assert "Bottleneck Evidence: B* bottlenecks and S* solution attempts" in idea_discovery
    assert "Evaluation Canon: platforms=[EC-P* summary], workloads=[EC-W* summary]" in idea_discovery
    assert "Gap Seeds: [top G* residual-gap seeds]" in idea_discovery


def test_research_pipeline_still_preserves_handoff_contract_ids() -> None:
    research_pipeline = read("skills/research-pipeline/SKILL.md")

    assert "`core_baseline` must be a `CB*` candidate or `new baseline with rationale`." in research_pipeline
    assert "`canon_mapping.platform` must reference `EC-P*`" in research_pipeline
    assert "`canon_mapping.workload` must reference `EC-W*`" in research_pipeline


def test_mock_landscape_pack_reference_rules_resolve() -> None:
    mock_pack = {
        "bottlenecks": {"B1", "B2"},
        "solutions": {"S1": ["B1", "B2"]},
        "platforms": {"EC-P1": ["B1", "S1"]},
        "workloads": {"EC-W1": ["B1"]},
        "baselines": {
            "CB1": {
                "addresses": ["B1", "S1"],
                "canon_mapping": "platform=[EC-P1]; workload=[EC-W1]",
            }
        },
        "gaps": {
            "G1": {
                "bottleneck_id": "B1",
                "source_residual": "S1.missing_piece",
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

    for baseline in mock_pack["baselines"].values():
        assert all(item in bottlenecks or item in solutions or item == "none_found" for item in baseline["addresses"])
        assert re.fullmatch(r"platform=\[EC-P\d+\]; workload=\[EC-W\d+\]", baseline["canon_mapping"])

    for gap in mock_pack["gaps"].values():
        assert gap["bottleneck_id"] in bottlenecks
        source_id, source_field = gap["source_residual"].split(".")
        assert (source_id in bottlenecks and source_field == "residual_gap") or (
            source_id in solutions and source_field == "missing_piece"
        )
