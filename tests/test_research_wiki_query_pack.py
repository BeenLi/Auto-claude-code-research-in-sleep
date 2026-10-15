from __future__ import annotations

import json
import re
import tempfile
import unittest
from pathlib import Path

from tools import research_wiki as wiki


class QueryPackRedesignTest(unittest.TestCase):
    def test_includes_projection_claim_experiment_gap_and_recent_edges(self):
        with tempfile.TemporaryDirectory(prefix="aris-query-pack-") as tmp:
            project = Path(tmp)
            wiki_root = project / "research-wiki"
            for subdir in ("papers", "ideas", "experiments", "claims", "graph"):
                (wiki_root / subdir).mkdir(parents=True, exist_ok=True)
            (project / "RESEARCH_BRIEF.md").write_text("LLM serving memory hierarchy research.")
            (wiki_root / "gap_map.md").write_text("# Gap Map\n\nG1: KV cache offload lacks tail-latency evidence.\n")
            (wiki_root / "papers" / "smith2025_kv.md").write_text(
                """---
type: paper
node_id: paper:smith2025_kv
title: "KV Cache Offload"
obsidian_path: "001-input/PaperRead/PaperNotes/KV.md"
---

# KV Cache Offload

<!-- BEGIN OBSIDIAN PROJECTION -->
## Agent Summary

- One-line: CXL offload reduces HBM pressure.
- Core problem: Long contexts exhaust GPU memory.
- Key insight: KV cache has hot and cold blocks.
- Method: Migrate cold blocks asynchronously.
- Limitations: Short contexts see little benefit.
- Reusable lessons: Tiered KV cache policies transfer to multi-GPU serving.

## Related Papers

- paper_ref: FlashAttention
<!-- END OBSIDIAN PROJECTION -->

<!-- BEGIN PROJECT NOTES -->
<!-- END PROJECT NOTES -->
"""
            )
            (wiki_root / "claims" / "C1.md").write_text(
                """---
type: claim
node_id: claim:C1
title: "CXL improves TTFT"
status: partial
---

# CXL improves TTFT

Tail latency improves only under long contexts.
"""
            )
            (wiki_root / "experiments" / "E1.md").write_text(
                """---
type: experiment
node_id: exp:E1
title: "Long-context serving trace"
linked_claim: claim:C1
---

# Long-context serving trace

## Setup
ShareGPT long-context replay.

## Result
p95 TTFT improved by 18%.
"""
            )
            (wiki_root / "graph" / "edges.jsonl").write_text(
                json.dumps(
                    {
                        "from": "exp:E1",
                        "to": "claim:C1",
                        "type": "supports",
                        "evidence": "p95 TTFT improved by 18%",
                    }
                )
                + "\n"
            )

            wiki.rebuild_query_pack(str(wiki_root), max_chars=8000)
            pack = (wiki_root / "query_pack.md").read_text()

        self.assertIn("LLM serving memory hierarchy", pack)
        self.assertIn("KV cache offload lacks tail-latency evidence", pack)
        self.assertIn("paper:smith2025_kv", pack)
        self.assertIn("CXL offload reduces HBM pressure", pack)
        self.assertIn("FlashAttention", pack)
        self.assertIn("claim:C1", pack)
        self.assertIn("partial", pack)
        self.assertIn("Tail latency improves", pack)
        self.assertIn("exp:E1", pack)
        self.assertIn("p95 TTFT improved by 18%", pack)
        self.assertIn("exp:E1 --supports--> claim:C1", pack)

    def _make_wiki(self, project: Path) -> Path:
        wiki_root = project / "research-wiki"
        wiki.init_wiki(str(wiki_root))
        return wiki_root

    def test_brief_sections_are_extracted_in_priority_order(self):
        with tempfile.TemporaryDirectory(prefix="aris-query-pack-") as tmp:
            project = Path(tmp)
            wiki_root = self._make_wiki(project)
            filler = "Background detail. " * 40  # pushes later sections past a flat slice
            (project / "RESEARCH_BRIEF.md").write_text(
                "# Research Brief\n\n"
                "## Problem Statement\nKV cache spills dominate tail latency.\n\n"
                f"## Background\n{filler}\n\n"
                "## Constraints\nOne node with 8 GPUs; no new silicon.\n\n"
                "## What I'm Looking For\nA host-memory tier policy.\n\n"
                "## Existing Results\nPilot shows 12% p95 gain.\n",
                encoding="utf-8",
            )
            wiki.rebuild_query_pack(str(wiki_root))
            pack = (wiki_root / "query_pack.md").read_text(encoding="utf-8")

        self.assertIn("**Problem**", pack)
        self.assertIn("One node with 8 GPUs", pack)
        self.assertIn("A host-memory tier policy", pack)
        # tolerant heading match: "Existing Results" resolves "Existing Results (if any)"
        self.assertIn("Pilot shows 12% p95 gain", pack)
        self.assertLess(pack.index("**Constraints**"), pack.index("**Background**"))

    def test_unenriched_paper_has_no_todo_thesis_or_dangling_colon(self):
        with tempfile.TemporaryDirectory(prefix="aris-query-pack-") as tmp:
            wiki_root = self._make_wiki(Path(tmp))
            wiki.ingest_paper(str(wiki_root), title="Attention Is All You Need",
                              authors=["Ashish Vaswani"], year=2017)
            wiki.ingest_paper(str(wiki_root), title="Paged KV Cache Serving",
                              authors=["Woosuk Kwon"], year=2023,
                              thesis="Paging removes KV fragmentation.")
            pack = (wiki_root / "query_pack.md").read_text(encoding="utf-8")

        self.assertNotIn("_TODO", pack)
        self.assertIn("] Attention Is All You Need\n", pack)
        self.assertIn("one_line=Paging removes KV fragmentation.", pack)

    def test_claim_idea_and_experiment_layers_project_into_pack_index_and_lint(self):
        with tempfile.TemporaryDirectory(prefix="aris-query-pack-") as tmp:
            wiki_root = self._make_wiki(Path(tmp))
            root = str(wiki_root)
            wiki.add_claim(root, "thm-ub", "Prefill bound", status="drafted",
                           statement="TTFT is bounded by the prefill term.")
            wiki.upsert_idea(root, "kv-tier", "Tiered KV cache", outcome="negative",
                             risks="Failed: PCIe bandwidth bound.")
            wiki.upsert_idea(root, "kv-cxl", "KV on CXL", stage="parked",
                             park_reason="designed_not_run",
                             revisit_condition="CXL expander available")
            wiki.add_experiment(root, "exp-001", idea="kv-tier", verdict="no",
                                hardware="8xH100", metrics="p95 TTFT +3%")
            # Age the drafted claim so lint flags it as stale.
            claim_page = wiki_root / "claims" / "thm-ub.md"
            text = claim_page.read_text(encoding="utf-8")
            claim_page.write_text(
                re.sub(r"(?m)^added: .*$", "added: 2000-01-01T00:00:00Z", text),
                encoding="utf-8")
            wiki.rebuild_query_pack(root)
            wiki.rebuild_index(root)
            report_path = wiki.lint_wiki(root)

            pack = (wiki_root / "query_pack.md").read_text(encoding="utf-8")
            index = (wiki_root / "index.md").read_text(encoding="utf-8")
            report = report_path.read_text(encoding="utf-8")

        self.assertIn("[claim:thm-ub] drafted: Prefill bound. TTFT is bounded", pack)
        self.assertIn("**Tiered KV cache**: Failed: PCIe bandwidth bound.", pack)
        self.assertNotIn("KV on CXL**", pack)  # parked/pending is not banlisted
        self.assertIn("[exp:exp-001]", pack)
        self.assertIn("setup=hardware=8xH100", pack)
        self.assertIn("verdict=no; linked=idea:kv-tier", pack)
        self.assertIn("`claim:thm-ub` — Prefill bound [drafted]", index)
        self.assertIn("`claim:thm-ub` is still drafted after", report)


if __name__ == "__main__":
    unittest.main()
