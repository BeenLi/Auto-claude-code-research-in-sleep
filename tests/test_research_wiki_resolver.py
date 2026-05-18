from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tools import research_wiki as wiki


def _projection(**overrides):
    values = {
        "path": Path("note.md"),
        "obsidian_path": "001-input/PaperRead/PaperNotes/note.md",
        "title": "A Collision Friendly Paper",
        "method_name": "",
        "authors": [],
        "year": 0,
        "venue": "",
        "tags": [],
        "zotero_item_id": "",
        "zotero_item_key": "",
        "zotero_key": "",
        "zotero_collection": "",
        "doi": "",
        "arxiv_id": "",
        "arxiv_html": "",
        "created": "",
        "fields": {},
        "related_papers": [],
    }
    values.update(overrides)
    return wiki.PaperProjection(**values)


class PaperIdentityResolverTest(unittest.TestCase):
    def test_matches_exact_identifiers_and_preserves_existing_page(self):
        with tempfile.TemporaryDirectory(prefix="aris-resolver-") as tmp:
            root = Path(tmp) / "research-wiki"
            (root / "papers").mkdir(parents=True)
            page = root / "papers" / "smith2025_cache.md"
            page.write_text(
                """---
type: paper
node_id: paper:stable-node
title: "Cache Paper"
external_ids:
  arxiv: "2501.12345"
  doi: "10.1145/cache"
zotero:
  item_id: 7
  item_key: ABC123
---

# Cache Paper
"""
            )

            index = wiki.load_wiki_paper_index(root)
            result = wiki.resolve_paper_identity(
                _projection(zotero_item_key="ABC123"),
                index,
            )

        self.assertEqual(result.status, "matched")
        self.assertEqual(result.entry.node_id, "paper:stable-node")
        self.assertEqual(result.entry.path.name, "smith2025_cache.md")

    def test_reports_conflict_when_one_note_matches_multiple_pages(self):
        with tempfile.TemporaryDirectory(prefix="aris-resolver-conflict-") as tmp:
            root = Path(tmp) / "research-wiki"
            (root / "papers").mkdir(parents=True)
            for name in ("a.md", "b.md"):
                (root / "papers" / name).write_text(
                    """---
type: paper
node_id: paper:%s
title: "Duplicate"
external_ids:
  doi: "10.1145/dup"
---

# Duplicate
""" % name[:-3]
                )

            result = wiki.resolve_paper_identity(
                _projection(doi="10.1145/dup"),
                wiki.load_wiki_paper_index(root),
            )

        self.assertEqual(result.status, "conflict")
        self.assertIn("doi", result.conflicts[0])

    def test_loose_title_and_method_matching_are_opt_in(self):
        with tempfile.TemporaryDirectory(prefix="aris-resolver-loose-") as tmp:
            root = Path(tmp) / "research-wiki"
            (root / "papers").mkdir(parents=True)
            (root / "papers" / "old.md").write_text(
                """---
type: paper
node_id: paper:old
title: "Normalized Title Match"
method_name: "Speculative Decoding"
---

# Normalized Title Match
"""
            )
            index = wiki.load_wiki_paper_index(root)
            projection = _projection(
                title="Normalized   title match!",
                method_name="Speculative Decoding",
            )

            strict = wiki.resolve_paper_identity(projection, index, match_loose=False)
            loose = wiki.resolve_paper_identity(projection, index, match_loose=True)

        self.assertEqual(strict.status, "new")
        self.assertEqual(loose.status, "matched")
        self.assertEqual(loose.entry.node_id, "paper:old")


if __name__ == "__main__":
    unittest.main()
