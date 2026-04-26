#!/usr/bin/env python3
"""Tests for the M1 analytical break-even evidence pack."""

import csv
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RX_ROOT = ROOT / "experiments" / "rx-expansion"
sys.path.insert(0, str(RX_ROOT))

from rx_expansion import analytical_model
import run_m1_break_even


class TestM1AnalyticalModel(unittest.TestCase):
    def test_output_utilization_increases_with_ratio_under_saturated_offered_load(self):
        low = analytical_model.evaluate_profile(
            ratio=1.2,
            link_gbps=400,
            output_bw_gbps=512,
            decompressor_input_gbps=800,
            decompressor_output_gbps=1024,
            offered_load_mode="compressed_line_rate_saturated",
            observation_window_us=100,
        )
        high = analytical_model.evaluate_profile(
            ratio=4.0,
            link_gbps=400,
            output_bw_gbps=512,
            decompressor_input_gbps=800,
            decompressor_output_gbps=1024,
            offered_load_mode="compressed_line_rate_saturated",
            observation_window_us=100,
        )

        self.assertGreater(high["output_utilization"], low["output_utilization"])
        self.assertGreater(high["max_expansion_debt_bytes"], low["max_expansion_debt_bytes"])
        self.assertTrue(low["is_output_safe"])
        self.assertFalse(high["is_output_safe"])

    def test_ratio_threshold_drops_when_output_budget_drops(self):
        high_budget = analytical_model.evaluate_profile(
            ratio=2.0,
            link_gbps=400,
            output_bw_gbps=800,
            decompressor_input_gbps=800,
            decompressor_output_gbps=1024,
            offered_load_mode="compressed_line_rate_saturated",
            observation_window_us=100,
        )
        low_budget = analytical_model.evaluate_profile(
            ratio=2.0,
            link_gbps=400,
            output_bw_gbps=256,
            decompressor_input_gbps=800,
            decompressor_output_gbps=1024,
            offered_load_mode="compressed_line_rate_saturated",
            observation_window_us=100,
        )

        self.assertLess(low_budget["ratio_threshold"], high_budget["ratio_threshold"])

    def test_same_original_bytes_mode_does_not_create_ratio_driven_output_demand(self):
        low = analytical_model.evaluate_profile(
            ratio=1.2,
            link_gbps=400,
            output_bw_gbps=512,
            decompressor_input_gbps=800,
            decompressor_output_gbps=1024,
            offered_load_mode="same_original_bytes",
            observation_window_us=100,
        )
        high = analytical_model.evaluate_profile(
            ratio=4.0,
            link_gbps=400,
            output_bw_gbps=512,
            decompressor_input_gbps=800,
            decompressor_output_gbps=1024,
            offered_load_mode="same_original_bytes",
            observation_window_us=100,
        )

        self.assertAlmostEqual(low["decompressed_output_gbps"], high["decompressed_output_gbps"])
        self.assertLess(high["compressed_ingress_gbps"], low["compressed_ingress_gbps"])

    def test_result_pack_preserves_provenance_and_p0_claim_scope(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            run_m1_break_even.run(
                config_path=RX_ROOT / "configs" / "m1_break_even.json",
                output_dir=output_dir,
            )

            json_path = output_dir / "m1_break_even.json"
            csv_path = output_dir / "m1_break_even.csv"
            report_path = output_dir / "M1_GO_NOGO_REPORT.md"
            self.assertTrue(json_path.exists())
            self.assertTrue(csv_path.exists())
            self.assertTrue(report_path.exists())

            payload = json.loads(json_path.read_text(encoding="utf-8"))
            rows = payload["results"]
            self.assertGreater(len(rows), 0)

            first = rows[0]
            for field in [
                "schedule_source",
                "payload_source",
                "evidence_level",
                "claim_scope",
                "source_pair",
                "pressure_interpretation",
            ]:
                self.assertIn(field, first)
            self.assertEqual(first["evidence_level"], "P0_literature_ratio")
            self.assertEqual(first["claim_scope"], "analytical_sensitivity_only")

            with csv_path.open("r", encoding="utf-8", newline="") as handle:
                csv_rows = list(csv.DictReader(handle))
            self.assertEqual(len(csv_rows), len(rows))
            self.assertEqual(csv_rows[0]["claim_scope"], "analytical_sensitivity_only")

            report = report_path.read_text(encoding="utf-8")
            self.assertIn("P0-only analytical sensitivity", report)
            self.assertIn("Go/No-Go", report)
            self.assertIn("same_original_bytes unsafe rows are fixed-output-path bottlenecks", report)
            self.assertNotIn("real communication payload claim allowed", report.lower())


if __name__ == "__main__":
    unittest.main()
