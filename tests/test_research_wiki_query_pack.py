from __future__ import annotations

import json
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


if __name__ == "__main__":
    unittest.main()
