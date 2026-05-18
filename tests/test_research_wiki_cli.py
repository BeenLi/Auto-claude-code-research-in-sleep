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


if __name__ == "__main__":
    unittest.main()
