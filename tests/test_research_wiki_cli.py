#!/usr/bin/env python3
"""CLI behavior tests for the research-wiki helper."""
from __future__ import annotations

import shutil
import subprocess
import tempfile
import time
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
HELPER = REPO_ROOT / "tools" / "research_wiki.py"


class ResearchWikiCliTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="aris-wiki-cli-"))
        self.wiki = self.tmp / "research-wiki"
        subprocess.run(
            ["python3", str(HELPER), "init", str(self.wiki)],
            check=True,
            text=True,
            capture_output=True,
        )

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def run_helper(self, *args: str):
        return subprocess.run(
            ["python3", str(HELPER), *args],
            cwd=self.tmp,
            text=True,
            capture_output=True,
        )

    def test_update_modifies_entity_frontmatter_and_rebuilds_query_pack(self):
        idea = self.wiki / "ideas" / "001.md"
        idea.write_text(
            """---
type: idea
node_id: idea:001
title: "KV cache compression"
stage: proposed
outcome: unknown
---

# KV cache compression

## Failure Notes
failed because decompression latency dominated
"""
        )

        result = self.run_helper(
            "update",
            str(self.wiki),
            "idea:001",
            "--field",
            "outcome",
            "--value",
            "negative",
        )

        self.assertEqual(result.returncode, 0, msg=result.stderr)
        updated = idea.read_text()
        self.assertIn("outcome: negative", updated)
        self.assertNotIn("outcome: unknown", updated)
        self.assertIn("KV cache compression", (self.wiki / "query_pack.md").read_text())
        self.assertIn("update: idea:001 outcome=negative", (self.wiki / "log.md").read_text())

    def test_lint_writes_report_for_orphans_stale_claims_and_contradictions(self):
        claim = self.wiki / "claims" / "C1.md"
        claim.write_text(
            """---
type: claim
node_id: claim:C1
title: "Compression improves TTFT"
status: reported
added: 2000-01-01T00:00:00Z
---

# Compression improves TTFT

## Evidence
_TODO._
"""
        )
        edges = self.wiki / "graph" / "edges.jsonl"
        edges.write_text(
            '{"from":"exp:e1","to":"claim:C1","type":"supports","evidence":""}\n'
            '{"from":"exp:e2","to":"claim:C1","type":"invalidates","evidence":""}\n'
        )

        result = self.run_helper("lint", str(self.wiki))

        self.assertEqual(result.returncode, 0, msg=result.stderr)
        report = (self.wiki / "LINT_REPORT.md").read_text()
        self.assertIn("Stale Claims", report)
        self.assertIn("claim:C1", report)
        self.assertIn("Contradictions", report)
        self.assertIn("both supports and invalidates", report)

    def test_public_skill_subcommands_query_and_ingest_are_supported(self):
        ingest = self.run_helper(
            "ingest",
            str(self.wiki),
            "--title",
            "Attention Is All You Need",
            "--authors",
            "Ashish Vaswani, Noam Shazeer",
            "--year",
            "2017",
            "--venue",
            "NeurIPS",
            "--tags",
            "transformer,attention",
        )
        self.assertEqual(ingest.returncode, 0, msg=ingest.stderr)
        self.assertTrue(list((self.wiki / "papers").glob("vaswani2017_attention*.md")))

        query = self.run_helper("query", str(self.wiki), "transformer serving")

        self.assertEqual(query.returncode, 0, msg=query.stderr)
        self.assertIn("Attention Is All You Need", (self.wiki / "query_pack.md").read_text())

    def test_sync_obsidian_dry_run_honors_limit_and_writes_report_only(self):
        notes = self.tmp / "PaperNotes"
        notes.mkdir()
        older = notes / "Older.md"
        newer = notes / "Newer.md"
        older.write_text(
            """---
title: "Older Paper"
authors: ["Old Author"]
year: 2024
---

## 一句话总结
old note
"""
        )
        newer.write_text(
            """---
title: "Newer Paper"
authors: ["New Author"]
year: 2025
---

## 一句话总结
new note
"""
        )
        old_time = time.time() - 100
        new_time = time.time()
        older.touch()
        newer.touch()
        older.chmod(0o644)
        newer.chmod(0o644)
        import os

        os.utime(older, (old_time, old_time))
        os.utime(newer, (new_time, new_time))
        log_before = (self.wiki / "log.md").read_text()
        report = self.tmp / "sync-report.md"

        result = self.run_helper(
            "sync-obsidian",
            str(self.wiki),
            "--paper-notes-dir",
            str(notes),
            "--dry-run",
            "--limit",
            "1",
            "--report",
            str(report),
        )

        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertFalse(list((self.wiki / "papers").glob("*.md")))
        self.assertEqual(log_before, (self.wiki / "log.md").read_text())
        report_text = report.read_text()
        self.assertIn("Newer Paper", report_text)
        self.assertNotIn("Older Paper", report_text)

    def test_sync_obsidian_writes_projection_rebuilds_pack_and_logs(self):
        notes = self.tmp / "PaperNotes"
        notes.mkdir()
        note = notes / "KV.md"
        note.write_text(
            """---
title: "KV Cache Offload"
method_name: "KV-Migrate"
authors: ["Alice Smith"]
year: 2025
doi: "10.1145/kv"
---

## 一句话总结
KV cache offload lowers HBM pressure.
"""
        )

        result = self.run_helper(
            "sync-obsidian",
            str(self.wiki),
            "--paper-notes-dir",
            str(notes),
        )

        self.assertEqual(result.returncode, 0, msg=result.stderr)
        page = next((self.wiki / "papers").glob("smith2025_*cache_offload.md"))
        content = page.read_text()
        self.assertIn("source: obsidian", content)
        self.assertIn("- One-line: KV cache offload lowers HBM pressure.", content)
        self.assertIn("KV Cache Offload", (self.wiki / "query_pack.md").read_text())
        self.assertIn("sync-obsidian:", (self.wiki / "log.md").read_text())

    def test_sync_obsidian_loose_matching_is_opt_in(self):
        existing = self.wiki / "papers" / "existing.md"
        existing.write_text(
            """---
type: paper
node_id: paper:existing
title: "Existing Paper"
method_name: "SharedMethod"
---

# Existing Paper

<!-- BEGIN OBSIDIAN PROJECTION -->
<!-- END OBSIDIAN PROJECTION -->

<!-- BEGIN PROJECT NOTES -->
manual note
<!-- END PROJECT NOTES -->
"""
        )
        notes = self.tmp / "PaperNotes"
        notes.mkdir()
        note = notes / "Incoming.md"
        note.write_text(
            """---
title: "Different Incoming Paper"
method_name: "SharedMethod"
authors: ["Alice Smith"]
year: 2025
---

## 一句话总结
incoming summary
"""
        )

        strict = self.run_helper(
            "sync-obsidian",
            str(self.wiki),
            "--paper-notes-dir",
            str(notes),
            "--dry-run",
        )
        loose = self.run_helper(
            "sync-obsidian",
            str(self.wiki),
            "--paper-notes-dir",
            str(notes),
            "--dry-run",
            "--match-loose",
        )

        self.assertEqual(strict.returncode, 0, msg=strict.stderr)
        self.assertEqual(loose.returncode, 0, msg=loose.stderr)
        self.assertIn("created: 1", strict.stdout)
        self.assertIn("updated: 1", loose.stdout)

    # The three node-layer writers are called by other skills with fixed flag
    # names (proof-checker -> add_claim, idea-creator -> upsert_idea,
    # result-to-claim -> add_experiment). These lock that CLI contract.

    def test_add_claim_cli_matches_proof_checker_call_site(self):
        result = self.run_helper(
            "add_claim", str(self.wiki),
            "--slug", "thm-main-ub", "--name", "Main upper bound",
            "--status", "sound-modulo-imports",
            "--provenance", ".aris/traces/proof-checker/run01/",
            "--statement", "TTFT is bounded by the prefill term.",
            "--scope", "Single node only.",
            "--evidence", "PROOF_AUDIT.json PASS modulo one import",
            "--update-on-exist",
        )
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        page = (self.wiki / "claims" / "thm-main-ub.md").read_text()
        self.assertIn("status: sound-modulo-imports", page)
        self.assertIn("claim:thm-main-ub", (self.wiki / "index.md").read_text())

        rejected = self.run_helper("add_claim", str(self.wiki), "--slug", "c-bad",
                                   "--name", "Bad", "--status", "supported")
        self.assertNotEqual(rejected.returncode, 0)
        self.assertIn("unknown claim status", rejected.stderr)
        self.assertFalse((self.wiki / "claims" / "c-bad.md").exists())

    def test_upsert_idea_cli_records_parked_pool_fields(self):
        result = self.run_helper(
            "upsert_idea", str(self.wiki),
            "--slug", "kv-cxl", "--title", "KV cache on CXL",
            "--stage", "parked", "--outcome", "pending",
            "--thesis", "Spill cold KV blocks to a CXL expander.",
            "--risks", "CXL latency may dominate.",
            "--based-on", "paper:smith2025_kv", "--target-gaps", "G1",
            "--park-reason", "designed_not_run",
            "--revisit-condition", "A CXL expander is listed in lab-resources.yaml",
        )
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        page = self.wiki / "ideas" / "kv-cxl.md"
        content = page.read_text()
        self.assertIn("stage: parked", content)
        self.assertIn('park_reason: "designed_not_run"', content)
        self.assertIn("revisit_condition:", content)
        edges = (self.wiki / "graph" / "edges.jsonl").read_text()
        self.assertIn('"type": "inspired_by"', edges)
        self.assertIn('"to": "gap:G1"', edges)

        missing = self.run_helper("upsert_idea", str(self.wiki), "--slug", "p2",
                                  "--title", "Parked without reason", "--stage", "parked")
        self.assertEqual(missing.returncode, 0, msg=missing.stderr)
        self.assertIn("--park-reason", missing.stderr)

        bad_stage = self.run_helper("upsert_idea", str(self.wiki), "--slug", "p3",
                                    "--title", "X", "--stage", "eliminated")
        self.assertNotEqual(bad_stage.returncode, 0)

    def test_idea_creator_flow_upsert_then_update_pool_fields(self):
        # /idea-creator Phase 7: upsert_idea with upstream flags, then `update`
        # writes the local candidate-pool fields onto the same page.
        result = self.run_helper(
            "upsert_idea", str(self.wiki),
            "--slug", "kv-tier", "--title", "Tiered KV cache",
            "--stage", "proposed", "--outcome", "pending",
            "--thesis", "Keep hot KV blocks in HBM.",
            "--risks", "If the outcome: negative path happens, PCIe dominates.",
            "--based-on", "paper:smith2025_kv", "--target-gaps", "G1",
        )
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        for field, value in [("pool_status", "parked"),
                             ("park_reason", "low_overall_merit"),
                             ("revisit_condition", "A CXL expander is in lab-resources.yaml")]:
            upd = self.run_helper("update", str(self.wiki), "idea:kv-tier",
                                  "--field", field, "--value", value)
            self.assertEqual(upd.returncode, 0, msg=upd.stderr)

        page = self.wiki / "ideas" / "kv-tier.md"
        content = page.read_text(encoding="utf-8")
        self.assertIn("pool_status: parked", content)
        self.assertIn("park_reason: low_overall_merit", content)
        self.assertIn('revisit_condition: "A CXL expander is in lab-resources.yaml"', content)
        self.assertIn("outcome: pending", content)
        self.assertIn('based_on: ["paper:smith2025_kv"]', content)
        self.assertIn("## Key risks", content)

        # A re-ideation run skips the existing page, so the pool fields survive.
        again = self.run_helper("upsert_idea", str(self.wiki), "--slug", "kv-tier",
                                "--title", "Tiered KV cache")
        self.assertEqual(again.returncode, 0, msg=again.stderr)
        self.assertIn("pool_status: parked", page.read_text(encoding="utf-8"))

        # The risks text mentions "outcome: negative" but the frontmatter says pending.
        pack = (self.wiki / "query_pack.md").read_text(encoding="utf-8")
        self.assertNotIn("Failed Ideas", pack)
        stats = self.run_helper("stats", str(self.wiki))
        self.assertIn("0 failed, 0 succeeded, 1 parked", stats.stdout)

        # A parked pool idea is untested on purpose; lint must not call it dead.
        lint = self.run_helper("lint", str(self.wiki))
        self.assertEqual(lint.returncode, 0, msg=lint.stderr)
        report = (self.wiki / "LINT_REPORT.md").read_text(encoding="utf-8")
        self.assertNotIn("`idea:kv-tier` is still proposed", report)

    def test_add_experiment_cli_matches_result_to_claim_call_site(self):
        result = self.run_helper(
            "add_experiment", str(self.wiki),
            "--slug", "exp-001", "--idea", "idea:kv-cxl",
            "--verdict", "partial", "--confidence", "high",
            "--date", "2026-10-15", "--hardware", "8xH100", "--duration", "2h",
            "--metrics", "p95 TTFT -12%", "--reasoning", "only long contexts improve",
            "--provenance", "EXPERIMENT_AUDIT.md", "--update-on-exist",
        )
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertIn("verdict: partial", (self.wiki / "experiments" / "exp-001.md").read_text())
        self.assertIn('"from": "idea:kv-cxl", "to": "exp:exp-001", "type": "tested_by"',
                      (self.wiki / "graph" / "edges.jsonl").read_text())

        bad = self.run_helper("add_experiment", str(self.wiki), "--slug", "exp-002",
                              "--verdict", "positive")
        self.assertNotEqual(bad.returncode, 0)


if __name__ == "__main__":
    unittest.main()
