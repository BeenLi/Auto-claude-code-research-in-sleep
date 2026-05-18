from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path

from tools import research_wiki as wiki


REPO_ROOT = Path(__file__).resolve().parent.parent
HELPER = REPO_ROOT / "tools" / "research_wiki.py"


def _projection(**overrides):
    values = {
        "path": Path("note.md"),
        "obsidian_path": "001-input/PaperRead/PaperNotes/note.md",
        "title": "Rendered Paper",
        "method_name": "RenderMethod",
        "authors": ["Alice Smith"],
        "year": 2025,
        "venue": "OSDI",
        "tags": ["llm"],
        "zotero_item_id": "7",
        "zotero_item_key": "ABC123",
        "zotero_key": "",
        "zotero_collection": "PaperRead",
        "doi": "10.1145/render",
        "arxiv_id": "2501.12345",
        "arxiv_html": "",
        "created": "",
        "fields": {"one_line": "One-line projection", "method": "Projected method"},
        "related_papers": ["FlashAttention"],
    }
    values.update(overrides)
    return wiki.PaperProjection(**values)


class WikiPaperRendererTest(unittest.TestCase):
    def test_replaces_projection_and_preserves_project_notes(self):
        existing = """---
type: paper
node_id: paper:rendered
title: "Old Title"
---

# Old Title

<!-- BEGIN OBSIDIAN PROJECTION -->
old generated content
<!-- END OBSIDIAN PROJECTION -->

<!-- BEGIN PROJECT NOTES -->
## Relevance to Current ARIS Project

Keep this exact manual note.
<!-- END PROJECT NOTES -->
"""

        rendered = wiki.render_wiki_paper_page(
            _projection(title="Rendered Paper"),
            slug="rendered",
            existing_text=existing,
        )

        self.assertIn("source: obsidian", rendered)
        self.assertIn("obsidian_path: \"001-input/PaperRead/PaperNotes/note.md\"", rendered)
        self.assertIn("- One-line: One-line projection", rendered)
        self.assertNotIn("old generated content", rendered)
        self.assertIn(
            "<!-- BEGIN PROJECT NOTES -->\n## Relevance to Current ARIS Project\n\n"
            "Keep this exact manual note.\n<!-- END PROJECT NOTES -->",
            rendered,
        )

    def test_legacy_page_without_markers_is_lazy_migrated_under_project_notes(self):
        legacy = """---
type: paper
node_id: paper:legacy
title: "Legacy"
added: 2026-05-01T00:00:00Z
custom_key: keep-me
---

# Legacy

## One-line thesis

Legacy thesis.

## Method

Legacy method note.
"""

        rendered = wiki.render_wiki_paper_page(
            _projection(title="Migrated"),
            slug="legacy",
            existing_text=legacy,
        )

        self.assertIn("legacy_added: 2026-05-01T00:00:00Z", rendered)
        self.assertIn("custom_key: keep-me", rendered)
        self.assertIn("## Legacy Wiki Content", rendered)
        self.assertIn("Legacy thesis.", rendered)
        self.assertIn("Legacy method note.", rendered)

    def test_ingest_paper_emits_projection_and_project_note_markers(self):
        with tempfile.TemporaryDirectory(prefix="aris-renderer-ingest-") as tmp:
            wiki_root = Path(tmp) / "research-wiki"
            subprocess.run(["python3", str(HELPER), "init", str(wiki_root)], check=True)

            result = subprocess.run(
                [
                    "python3",
                    str(HELPER),
                    "ingest_paper",
                    str(wiki_root),
                    "--title",
                    "Attention Is All You Need",
                    "--authors",
                    "Ashish Vaswani, Noam Shazeer",
                    "--year",
                    "2017",
                    "--venue",
                    "NeurIPS",
                    "--thesis",
                    "Transformer attention replaces recurrence.",
                ],
                text=True,
                capture_output=True,
            )
            self.assertEqual(result.returncode, 0, msg=result.stderr)
            page = next((wiki_root / "papers").glob("vaswani2017_attention*.md"))
            content = page.read_text()

        self.assertIn("<!-- BEGIN OBSIDIAN PROJECTION -->", content)
        self.assertIn("<!-- BEGIN PROJECT NOTES -->", content)
        self.assertIn("## One-line thesis", content)
        self.assertIn("Transformer attention replaces recurrence.", content)


if __name__ == "__main__":
    unittest.main()
