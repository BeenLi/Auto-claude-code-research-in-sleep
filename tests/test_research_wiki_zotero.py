from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path

from tools import research_wiki as wiki


def _projection(**overrides):
    values = {
        "path": Path("note.md"),
        "obsidian_path": "PaperNotes/note.md",
        "title": "",
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


def _write_zotero_fixture(path: Path):
    conn = sqlite3.connect(path)
    conn.executescript(
        """
        CREATE TABLE items (itemID INTEGER PRIMARY KEY, key TEXT);
        CREATE TABLE fields (fieldID INTEGER PRIMARY KEY, fieldName TEXT);
        CREATE TABLE itemData (itemID INTEGER, fieldID INTEGER, valueID INTEGER);
        CREATE TABLE itemDataValues (valueID INTEGER PRIMARY KEY, value TEXT);
        CREATE TABLE creators (creatorID INTEGER PRIMARY KEY, firstName TEXT, lastName TEXT);
        CREATE TABLE itemCreators (itemID INTEGER, creatorID INTEGER, orderIndex INTEGER);
        CREATE TABLE collections (collectionID INTEGER PRIMARY KEY, collectionName TEXT);
        CREATE TABLE collectionItems (collectionID INTEGER, itemID INTEGER);
        INSERT INTO items VALUES (7, 'ABC123');
        INSERT INTO fields VALUES (1, 'title'), (2, 'DOI'), (3, 'date'), (4, 'publicationTitle'), (5, 'archiveID');
        INSERT INTO itemData VALUES (7, 1, 1), (7, 2, 2), (7, 3, 3), (7, 4, 4), (7, 5, 5);
        INSERT INTO itemDataValues VALUES
          (1, 'Zotero Metadata Paper'),
          (2, '10.1145/zotero'),
          (3, '2025-03-01'),
          (4, 'OSDI'),
          (5, 'arXiv:2501.12345');
        INSERT INTO creators VALUES (1, 'Alice', 'Smith'), (2, 'Bob', 'Lee');
        INSERT INTO itemCreators VALUES (7, 1, 0), (7, 2, 1);
        INSERT INTO collections VALUES (1, 'PaperRead');
        INSERT INTO collectionItems VALUES (1, 7);
        """
    )
    conn.commit()
    conn.close()


class ZoteroEnrichmentTest(unittest.TestCase):
    def test_reads_metadata_by_item_key_through_copy_fallback_and_fills_empty_fields(self):
        with tempfile.TemporaryDirectory(prefix="aris-zotero-") as tmp:
            db = Path(tmp) / "zotero.sqlite"
            _write_zotero_fixture(db)
            (Path(tmp) / "zotero.sqlite-wal").write_text("lock marker")

            projection = _projection(zotero_item_key="ABC123")
            enriched, conflicts = wiki.enrich_projection_from_zotero(projection, db)

        self.assertEqual(conflicts, [])
        self.assertEqual(enriched.title, "Zotero Metadata Paper")
        self.assertEqual(enriched.authors, ["Alice Smith", "Bob Lee"])
        self.assertEqual(enriched.year, 2025)
        self.assertEqual(enriched.venue, "OSDI")
        self.assertEqual(enriched.doi, "10.1145/zotero")
        self.assertEqual(enriched.arxiv_id, "2501.12345")
        self.assertEqual(enriched.zotero_collection, "PaperRead")

    def test_reports_conflicts_without_overwriting_obsidian_values(self):
        with tempfile.TemporaryDirectory(prefix="aris-zotero-conflict-") as tmp:
            db = Path(tmp) / "zotero.sqlite"
            _write_zotero_fixture(db)

            projection = _projection(
                zotero_item_id="7",
                title="Obsidian Title",
                doi="10.1145/obsidian",
                year=2024,
            )
            enriched, conflicts = wiki.enrich_projection_from_zotero(projection, db)

        self.assertEqual(enriched.title, "Obsidian Title")
        self.assertEqual(enriched.doi, "10.1145/obsidian")
        self.assertEqual(enriched.year, 2024)
        self.assertTrue(any("title" in conflict for conflict in conflicts))
        self.assertTrue(any("doi" in conflict for conflict in conflicts))
        self.assertTrue(any("year" in conflict for conflict in conflicts))


if __name__ == "__main__":
    unittest.main()
