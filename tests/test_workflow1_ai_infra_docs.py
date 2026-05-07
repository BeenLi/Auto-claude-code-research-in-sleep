#!/usr/bin/env python3
"""Contract checks for Workflow 1 AI infrastructure migration docs."""

import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read_doc(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


class TestWorkflow1AIInfrastructureDocs(unittest.TestCase):
    def test_agent_status_entrypoints_are_symlinks(self):
        for path in ["AGENTS.md", "CLAUDE.md", "GEMINI.md"]:
            with self.subTest(path=path):
                entry = ROOT / path
                self.assertTrue(entry.is_symlink(), f"{path} must be a symlink")
                self.assertEqual(Path("AGENT.md"), entry.readlink())
                self.assertEqual((ROOT / "AGENT.md").resolve(), entry.resolve())

    def test_research_lit_uses_canonical_literature_review_output(self):
        for path in [
            "skills/research-lit/SKILL.md",
            "skills/skills-codex/research-lit/SKILL.md",
        ]:
            with self.subTest(path=path):
                doc = read_doc(path)
                self.assertTrue(doc.startswith("---\n"), f"{path} must use YAML frontmatter")
                self.assertIn("idea-stage/LITERATURE_REVIEW.md", doc)
                self.assertIn("LITERATURE_REVIEW_{YYYYMMDD_HHmmssZ}.md", doc)
                self.assertIn("date -u +%Y%m%d_%H%M%SZ", doc)
                self.assertNotIn("topic-slug", doc)
                self.assertNotIn("topic slug", doc.lower())
                self.assertNotIn("{project-root}/{topic-slug}/research-lit", doc)
                self.assertNotIn("{topic-slug}/papers", doc)

    def test_idea_creator_loads_canonical_literature_review(self):
        for path in [
            "skills/idea-creator/SKILL.md",
            "skills/skills-codex/idea-creator/SKILL.md",
        ]:
            with self.subTest(path=path):
                doc = read_doc(path)
                self.assertIn("idea-stage/LITERATURE_REVIEW.md", doc)
                self.assertNotIn("topic-slug", doc)
                self.assertNotIn("topic slug", doc.lower())
                self.assertNotIn("{project-root}/{topic-slug}/research-lit", doc)

    def test_active_contract_points_to_research_contract(self):
        for path in [
            "AGENT.md",
            "AGENTS.md",
            "CLAUDE.md",
            "GEMINI.md",
            "templates/AGENT_MD_TEMPLATE.md",
            "templates/CLAUDE_MD_TEMPLATE.md",
        ]:
            with self.subTest(path=path):
                doc = read_doc(path)
                self.assertIn("contract: idea-stage/docs/research_contract.md", doc)
                self.assertIn("Read idea-stage/docs/research_contract.md", doc)
                self.assertNotIn("contract: refine-logs/EXPERIMENT_PLAN.md", doc)
        for path in ["AGENT.md", "AGENTS.md", "CLAUDE.md", "GEMINI.md"]:
            with self.subTest(path=path):
                doc = read_doc(path)
                self.assertIn("Reads `refine-logs/EXPERIMENT_PLAN.md`", doc)

    def test_research_contract_exists_and_contains_current_state(self):
        doc = read_doc("idea-stage/docs/research_contract.md")
        for token in [
            "C-Share",
            "Core Claims",
            "Method Summary",
            "Experiment Design Pointer",
            "Claim Boundary",
            "Key Decisions",
            "Current Evidence Status",
            "Immediate Research Gate",
            "refine-logs/EXPERIMENT_PLAN.md",
            "shared compression-service fairness",
            "No C-Share experiments have been executed yet",
        ]:
            self.assertIn(token, doc)
        self.assertNotIn("## Status", doc)
        self.assertNotIn("## Next Step", doc)

    def test_workflow_skills_maintain_research_contract_postcondition(self):
        for path in [
            "skills/idea-discovery/SKILL.md",
            "skills/skills-codex/idea-discovery/SKILL.md",
            "skills/research-refine-pipeline/SKILL.md",
            "skills/skills-codex/research-refine-pipeline/SKILL.md",
            "skills/experiment-plan/SKILL.md",
            "skills/skills-codex/experiment-plan/SKILL.md",
            "skills/experiment-bridge/SKILL.md",
            "skills/skills-codex/experiment-bridge/SKILL.md",
            "skills/result-to-claim/SKILL.md",
            "skills/skills-codex/result-to-claim/SKILL.md",
        ]:
            with self.subTest(path=path):
                doc = read_doc(path)
                self.assertIn("idea-stage/docs/research_contract.md", doc)
                self.assertIn("research contract postcondition", doc.lower())
                match = re.search(
                    r"(?ims)^#{2,4} .*research contract postcondition.*?\n(?P<body>.*?)(?=^#{2,4} |\Z)",
                    doc,
                )
                self.assertIsNotNone(match)
                body = match.group("body")
                non_empty_lines = [line for line in body.splitlines() if line.strip()]
                self.assertLessEqual(len(non_empty_lines), 4)
                self.assertNotIn("Current Evidence Status", body)
                self.assertNotIn("Immediate Research Gate", body)

    def test_research_contract_protocol_uses_template_as_structure_source(self):
        for path in [
            "skills/shared-references/research-contract-maintenance.md",
            "skills/skills-codex/shared-references/research-contract-maintenance.md",
        ]:
            with self.subTest(path=path):
                doc = read_doc(path)
                self.assertIn("templates/RESEARCH_CONTRACT_TEMPLATE.md", doc)
                self.assertIn("structural template", doc.lower())
                self.assertNotIn("## Required Sections", doc)
                self.assertNotIn("## Structural Invariants", doc)

    def test_idea_failure_refreshes_contract_from_candidate_pool(self):
        for path in [
            "AGENT.md",
            "AGENTS.md",
            "CLAUDE.md",
            "GEMINI.md",
            "skills/shared-references/research-contract-maintenance.md",
            "skills/skills-codex/shared-references/research-contract-maintenance.md",
        ]:
            with self.subTest(path=path):
                doc = read_doc(path)
                self.assertIn("IDEA_CANDIDATES.md", doc)
                self.assertIn("idea fails", doc.lower())
                self.assertIn("overwrite", doc.lower())

    def test_experiment_plan_has_single_semantic_owner(self):
        for path in [
            "skills/idea-discovery/SKILL.md",
            "skills/skills-codex/idea-discovery/SKILL.md",
            "skills/research-refine-pipeline/SKILL.md",
            "skills/skills-codex/research-refine-pipeline/SKILL.md",
        ]:
            with self.subTest(path=path):
                doc = read_doc(path)
                self.assertIn("experiment-plan is the semantic owner", doc.lower())

    def test_experiment_plan_remains_execution_blueprint(self):
        experiment_plan = read_doc("skills/experiment-plan/SKILL.md")
        experiment_bridge = read_doc("skills/experiment-bridge/SKILL.md")
        self.assertIn("Write `refine-logs/EXPERIMENT_PLAN.md`", experiment_plan)
        self.assertIn("refine-logs/EXPERIMENT_PLAN.md", experiment_bridge)
        self.assertNotIn("session recovery", experiment_plan.lower())
        self.assertNotIn("session recovery", experiment_bridge.lower())

    def test_no_stale_research_contract_path_or_topic_slug_in_active_docs(self):
        paths = [
            "AGENT.md",
            "AGENTS.md",
            "CLAUDE.md",
            "GEMINI.md",
            "docs/PROJECT_FILES_GUIDE.md",
            "docs/PROJECT_FILES_GUIDE_CN.md",
            "docs/SESSION_RECOVERY_GUIDE.md",
            "docs/SESSION_RECOVERY_GUIDE_CN.md",
            "skills/research-lit/SKILL.md",
            "skills/skills-codex/research-lit/SKILL.md",
            "skills/idea-creator/SKILL.md",
            "skills/skills-codex/idea-creator/SKILL.md",
            "skills/result-to-claim/SKILL.md",
            "skills/skills-codex/result-to-claim/SKILL.md",
            "skills/ablation-planner/SKILL.md",
            "skills/skills-codex/ablation-planner/SKILL.md",
            "skills/paper-plan/SKILL.md",
            "skills/skills-codex/paper-plan/SKILL.md",
            "skills/auto-review-loop/SKILL.md",
            "skills/skills-codex/auto-review-loop/SKILL.md",
            "templates/AGENT_MD_TEMPLATE.md",
            "templates/CLAUDE_MD_TEMPLATE.md",
            "templates/IDEA_CANDIDATES_TEMPLATE.md",
            "templates/IDEA_CANDIDATES_TEMPLATE_CN.md",
        ]
        for path in paths:
            with self.subTest(path=path):
                doc = read_doc(path)
                self.assertIsNone(re.search(r"(?<!idea-stage/)docs/research_contract\.md", doc))
                self.assertNotIn("topic-slug", doc)
                self.assertNotIn("{topic-slug}", doc)
                self.assertNotIn("{project-root}/{topic-slug}/research-lit", doc)

    def test_claim_bearing_skills_read_research_contract(self):
        for path in [
            "skills/experiment-bridge/SKILL.md",
            "skills/skills-codex/experiment-bridge/SKILL.md",
            "skills/ablation-planner/SKILL.md",
            "skills/skills-codex/ablation-planner/SKILL.md",
            "skills/result-to-claim/SKILL.md",
            "skills/skills-codex/result-to-claim/SKILL.md",
            "skills/paper-plan/SKILL.md",
            "skills/skills-codex/paper-plan/SKILL.md",
            "skills/auto-review-loop/SKILL.md",
            "skills/skills-codex/auto-review-loop/SKILL.md",
        ]:
            with self.subTest(path=path):
                doc = read_doc(path)
                self.assertIn("idea-stage/docs/research_contract.md", doc)
                self.assertRegex(doc.lower(), r"claim boundary|intended claims|claim-bearing")

    def test_research_lit_defines_landscape_pack_contract(self):
        doc = read_doc("skills/research-lit/SKILL.md")

        for token in [
            "AI infrastructure for LLM",
            "compute/accelerator",
            "memory/storage/data movement",
            "interconnect/network",
            "runtime/system",
            "Landscape Pack",
            "Gap Seeds",
            "evidence_level",
            "minimum validation backend",
        ]:
            self.assertIn(token, doc)

    def test_idea_creator_reports_evaluation_handoff_fields(self):
        doc = read_doc("skills/idea-creator/SKILL.md")

        for token in [
            "canon_mapping",
            "core_baseline",
            "metrics",
            "target_validation_style",
            "evaluation_target_clarity",
            "evaluation_target_feasibility",
            "baseline_reproducibility",
            "evaluation_environment_access",
            "idea_adapter_cost",
            "pilot_runtime_cost",
            "handoff_to_workflow_1_5",
        ]:
            self.assertIn(token, doc)

        self.assertNotIn("deploy to GPU", doc)
        self.assertNotIn("Requires > 1 week GPU time", doc)

    def test_idea_discovery_defines_handoff_controls(self):
        doc = read_doc("skills/idea-discovery/SKILL.md")

        for token in [
            "MAX_HANDOFF_IDEAS = 6",
            "MAX_READY_FOR_WORKFLOW_1_5 = 3",
            "AUTO_PROCEED = true",
            "Literature Survey",
            "Idea Generation",
            "Deep Novelty Verification",
            "External Critical Review",
            "Method Refinement",
            "Final Report",
        ]:
            self.assertIn(token, doc)

    def test_refine_and_review_are_not_rdma_only(self):
        review_doc = read_doc("skills/research-review/SKILL.md")
        refine_doc = read_doc("skills/research-refine/SKILL.md")

        for doc in [review_doc, refine_doc]:
            self.assertIn("AI infrastructure for LLM", doc)
            self.assertRegex(
                doc,
                re.compile(r"compute.*memory.*interconnect.*runtime", re.IGNORECASE | re.DOTALL),
            )
            self.assertNotIn("Domain: NIC/DPU-side hardware systems and RDMA networking.", doc)


if __name__ == "__main__":
    unittest.main()
