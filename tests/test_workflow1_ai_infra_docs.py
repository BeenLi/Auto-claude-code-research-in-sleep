#!/usr/bin/env python3
"""Contract checks for Workflow 1 AI infrastructure migration docs."""

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read_doc(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


class TestWorkflow1AIInfrastructureDocs(unittest.TestCase):
    def test_research_lit_defines_landscape_pack_contract(self):
        doc = read_doc("skills/research-lit/SKILL.md")

        for token in [
            "AI infrastructure for LLM",
            "compute/accelerator",
            "memory/data movement",
            "interconnect/network",
            "storage/checkpoint/data pipeline",
            "runtime/serving",
            "Landscape Pack",
            "Gap Seeds",
            "evidence_level",
            "minimum validation backend",
        ]:
            self.assertIn(token, doc)

    def test_idea_creator_reports_architecture_pilot_fields(self):
        doc = read_doc("skills/idea-creator/SKILL.md")

        for token in [
            "ai_infra_layer",
            "hardware_bottleneck",
            "validation_backend",
            "pilot_status",
            "pilot_budget",
            "pilot_command_or_plan",
            "key_metric",
            "signal",
            "readiness_blocker",
            "Rx decompression expansion pressure",
        ]:
            self.assertIn(token, doc)

        self.assertNotIn("deploy to GPU", doc)
        self.assertNotIn("Requires > 1 week GPU time", doc)

    def test_idea_discovery_defines_checkpoint_modes(self):
        doc = read_doc("skills/idea-discovery/SKILL.md")

        for token in [
            "CHECKPOINT_MODE = `standard`",
            "CHECKPOINTS = `literature_scope, idea_selection`",
            "standard",
            "auto",
            "strict",
            "custom",
            "literature_scope",
            "idea_selection",
            "pre_refine",
            "final_report",
        ]:
            self.assertIn(token, doc)

    def test_refine_and_review_are_not_rdma_only(self):
        review_doc = read_doc("skills/research-review/SKILL.md")
        refine_doc = read_doc("skills/research-refine/SKILL.md")

        for doc in [review_doc, refine_doc]:
            self.assertIn("AI infrastructure for LLM", doc)
            self.assertIn("compute, memory/data movement, interconnect/network, storage/data pipeline, or runtime/serving", doc)
            self.assertNotIn("Domain: NIC/DPU-side hardware systems and RDMA networking.", doc)


if __name__ == "__main__":
    unittest.main()
