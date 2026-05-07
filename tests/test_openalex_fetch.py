import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "tools" / "openalex_fetch.py"


def load_module():
    spec = importlib.util.spec_from_file_location("openalex_fetch", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class OpenAlexFetchTests(unittest.TestCase):
    def test_parse_work_handles_null_primary_location_source(self):
        openalex_fetch = load_module()
        client = openalex_fetch.OpenAlexClient()

        work = {
            "id": "https://openalex.org/W123",
            "display_name": "Characterizing Lossy and Lossless Compression on Emerging BlueField DPU Architectures",
            "authorships": [
                {"author": {"display_name": "Ada Lovelace"}},
                {"author": {"display_name": "Grace Hopper"}},
            ],
            "primary_location": {"source": None},
            "open_access": {
                "is_oa": True,
                "oa_status": "green",
                "oa_url": "https://example.org/paper.pdf",
            },
            "topics": [{"display_name": "Computer architecture"}],
            "keywords": [{"display_name": "SmartNIC"}],
        }

        parsed = client._parse_work(work)

        self.assertEqual(parsed["venue"], "Unknown")
        self.assertIsNone(parsed["venue_type"])
        self.assertIs(parsed["is_oa"], True)
        self.assertEqual(parsed["oa_status"], "green")
        self.assertEqual(parsed["authors"], ["Ada Lovelace", "Grace Hopper"])


if __name__ == "__main__":
    unittest.main()
