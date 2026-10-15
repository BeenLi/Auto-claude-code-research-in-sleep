"""Local coverage for upstream fixes ported onto the customized research_wiki.py.

- Legacy-encoding wikis (upstream #391): every wiki read path, including the
  local-only lint / update / index paths, names the offending file instead of
  raising a bare UnicodeDecodeError.
- arXiv HTTP 406 is re-issued through curl (upstream e64c347).
- `sync` fetches all ids in ONE id_list request and falls back per id for misses
  (upstream #266).
"""
from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
import urllib.error
from io import BytesIO
from pathlib import Path
from unittest import mock

MODULE_PATH = Path(__file__).resolve().parents[1] / "tools" / "research_wiki.py"


def load_module():
    spec = importlib.util.spec_from_file_location("research_wiki_local_ports", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module  # dataclasses resolve their module via sys.modules
    spec.loader.exec_module(module)
    return module


rw = load_module()

ENTRY_XML = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom" xmlns:arxiv="http://arxiv.org/schemas/atom">
{entries}
</feed>"""

ENTRY = """  <entry>
    <id>http://arxiv.org/abs/{aid}v1</id>
    <title>{title}</title>
    <summary>Abstract.</summary>
    <published>2025-01-02T00:00:00Z</published>
    <author><name>{author}</name></author>
  </entry>"""


def feed(*items: tuple[str, str, str]) -> bytes:
    body = "\n".join(ENTRY.format(aid=a, title=t, author=n) for a, t, n in items)
    return ENTRY_XML.format(entries=body).encode("utf-8")


class FakeResponse:
    def __init__(self, body: bytes):
        self._body = body

    def read(self):
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False


class TestLegacyEncodingIsNamed(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        rw.init_wiki(str(self.root))
        self.bad = self.root / "ideas" / "legacy.md"
        self.bad.write_bytes("---\ntitle: 旧编码想法\n---\n".encode("gb18030"))

    def _assert_named(self, func, *args):
        with self.assertRaises(SystemExit) as ctx:
            func(*args)
        self.assertIn(str(self.bad), str(ctx.exception))
        self.assertIn("not valid UTF-8", str(ctx.exception))

    def test_index_query_pack_lint_and_stats_name_the_file(self):
        self._assert_named(rw.rebuild_index, str(self.root))
        self._assert_named(rw.rebuild_query_pack, str(self.root))
        self._assert_named(rw.lint_wiki, str(self.root))
        self._assert_named(rw.get_stats, str(self.root))

    def test_legacy_edges_file_is_named(self):
        self.bad.unlink()
        edges = self.root / "graph" / "edges.jsonl"
        edges.write_bytes('{"from": "paper:a", "to": "paper:b", "type": "extends", '
                          '"evidence": "中文"}\n'.encode("gb18030"))
        self.bad = edges
        self._assert_named(rw.add_edge, str(self.root), "paper:c", "paper:d", "extends")
        self._assert_named(rw.rebuild_query_pack, str(self.root))


class TestArxivFetchPorts(unittest.TestCase):
    def test_http_406_is_rescued_through_curl(self):
        err_406 = urllib.error.HTTPError(url="https://example/", code=406, msg="Not Acceptable",
                                         hdrs=None, fp=BytesIO(b""))
        body = feed(("2501.00001", "Rescued Paper", "Ada Lovelace"))
        with mock.patch.object(rw.urllib.request, "urlopen", side_effect=err_406), \
                mock.patch.object(rw, "_curl_get", return_value=body) as curl, \
                mock.patch.object(rw.time, "sleep", lambda _s: None):
            meta = rw.fetch_arxiv_metadata("2501.00001")
        self.assertEqual(meta["title"], "Rescued Paper")
        headers = curl.call_args[0][1]
        self.assertTrue(headers["User-Agent"].startswith("ARIS-research-wiki/"))

    def test_sync_uses_one_batch_request_and_falls_back_for_misses(self):
        root = Path(tempfile.mkdtemp())
        rw.init_wiki(str(root))
        requests = []
        responses = [
            # batch returns only the first id
            feed(("2501.00001", "Batched Paper", "Ada Lovelace")),
            # per-id fallback for the miss
            feed(("2501.00002", "Fallback Paper", "Grace Hopper")),
        ]

        def fake_urlopen(req, timeout=None):
            requests.append(req.full_url)
            return FakeResponse(responses.pop(0))

        with mock.patch.object(rw.urllib.request, "urlopen", side_effect=fake_urlopen), \
                mock.patch.object(rw.time, "sleep", lambda _s: None):
            rw.sync_papers(str(root), ["2501.00001", "2501.00002v3"])

        self.assertEqual(len(requests), 2)
        self.assertIn("id_list=2501.00001,2501.00002", requests[0])
        self.assertIn("max_results=2", requests[0])
        titles = sorted(p.read_text(encoding="utf-8").split("title: ", 1)[1].split("\n", 1)[0]
                        for p in (root / "papers").glob("*.md"))
        self.assertEqual(titles, ['"Batched Paper"', '"Fallback Paper"'])


if __name__ == "__main__":
    unittest.main()
