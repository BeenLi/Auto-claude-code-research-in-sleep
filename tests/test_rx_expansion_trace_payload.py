#!/usr/bin/env python3
"""Tests for the Rx expansion trace/payload evidence split."""

import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RX_ROOT = ROOT / "experiments" / "rx-expansion"
sys.path.insert(0, str(RX_ROOT))

from rx_expansion import trace_payload
from rx_expansion import ddp_capture
from rx_expansion import lz4_measure
from rx_expansion import schedule_adapters


class TestTracePayloadEvidence(unittest.TestCase):
    def test_compression_profiles_require_provenance_and_reject_fake_real_synthetic(self):
        valid = {
            "codec_family": "lz4",
            "payload_source": "local_tensor_checkpoint.bin",
            "evidence_level": "P1_real_tensor_bytes",
            "original_bytes": 4096,
            "compressed_bytes": 2048,
            "ratio": 2.0,
            "chunk_size": 4096,
            "dtype": "uint8",
            "tensor_role": "checkpoint",
            "provenance": "local file measured with /opt/homebrew/bin/lz4",
        }

        normalized = trace_payload.validate_compression_profiles([valid])

        self.assertEqual(normalized[0]["payload_realism"], "real_tensor_bytes")

        synthetic_as_real = dict(valid)
        synthetic_as_real["payload_source"] = "synthetic_zero_tensor"
        with self.assertRaisesRegex(trace_payload.ProvenanceError, "synthetic"):
            trace_payload.validate_compression_profiles([synthetic_as_real])

        missing_source = dict(valid)
        del missing_source["payload_source"]
        with self.assertRaisesRegex(trace_payload.ProvenanceError, "payload_source"):
            trace_payload.validate_compression_profiles([missing_source])

    def test_chakra_schedule_is_schedule_only_and_cannot_claim_payload_realism(self):
        schedule = [
            {
                "timestamp_ns": 100,
                "op_type": "ALL_REDUCE",
                "message_bytes": 8192,
                "src": "rank0",
                "dst": "rank1",
                "flow_id": "flow0",
                "tenant_id": "tenant0",
                "phase": "backward",
            }
        ]

        normalized = trace_payload.validate_schedule_trace(
            schedule,
            schedule_source="chakra_resnet_example",
        )

        self.assertEqual(normalized[0]["schedule_source"], "chakra_resnet_example")
        self.assertEqual(normalized[0]["schedule_realism"], "schedule_only")
        self.assertNotIn("payload_source", normalized[0])

    def test_chakra_adapter_normalizes_only_comm_nodes_as_schedule_only(self):
        nodes = [
            {
                "id": 7,
                "name": "nccl_all_reduce_bucket_7",
                "type": "COMM_COLL_NODE",
                "start_time_micros": 12,
                "attr": [
                    {"name": "message_bytes", "int64_val": 16384},
                    {"name": "collective", "string_val": "ALL_REDUCE"},
                    {"name": "src", "string_val": "rank0"},
                    {"name": "dst", "string_val": "rank1"},
                    {"name": "tenant_id", "string_val": "training"},
                    {"name": "phase", "string_val": "backward"},
                ],
            },
            {
                "id": 8,
                "name": "matmul",
                "type": "COMP_NODE",
                "start_time_micros": 13,
                "attr": [{"name": "message_bytes", "int64_val": 999999}],
            },
        ]

        schedule = schedule_adapters.chakra_nodes_to_schedule_trace(
            nodes,
            schedule_source="chakra_unit_trace",
        )

        self.assertEqual(len(schedule), 1)
        self.assertEqual(schedule[0]["timestamp_ns"], 12000)
        self.assertEqual(schedule[0]["op_type"], "ALL_REDUCE")
        self.assertEqual(schedule[0]["message_bytes"], 16384)
        self.assertEqual(schedule[0]["schedule_realism"], "schedule_only")
        self.assertNotIn("payload_source", schedule[0])

    def test_composition_preserves_schedule_and_payload_provenance(self):
        schedule = [
            {
                "timestamp_ns": 100,
                "op_type": "ALL_REDUCE",
                "message_bytes": 8192,
                "src": "rank0",
                "dst": "rank1",
                "flow_id": "flow0",
                "tenant_id": "tenant0",
                "phase": "backward",
            }
        ]
        profiles = [
            {
                "codec_family": "ebpc",
                "payload_source": "ebpc_alexnet_literature",
                "evidence_level": "P0_literature_ratio",
                "original_bytes": 5100,
                "compressed_bytes": 1000,
                "ratio": 5.1,
                "chunk_size": 4096,
                "dtype": "int8",
                "tensor_role": "feature_or_gradient_map",
                "provenance": "Cavigelli et al. 2019 reports AlexNet average 5.1x.",
            }
        ]

        rows = trace_payload.compose_ratio_trace(
            schedule,
            profiles,
            schedule_source="chakra_resnet_example",
        )

        self.assertEqual(len(rows), 2)
        first = rows[0]
        self.assertEqual(first["schedule_source"], "chakra_resnet_example")
        self.assertEqual(first["payload_source"], "ebpc_alexnet_literature")
        self.assertEqual(first["evidence_level"], "P0_literature_ratio")
        self.assertEqual(first["source_pair"], "chakra_resnet_example + P0_literature_ratio:ebpc_alexnet_literature")
        self.assertEqual(first["original_bytes"], 4096)
        self.assertEqual(first["compressed_bytes"], 804)
        self.assertEqual(rows[1]["original_bytes"], 4096)

    def test_claim_scope_requires_p2_or_p3_for_real_comm_payload_claim(self):
        p0 = [{"evidence_level": "P0_literature_ratio"}]
        p1 = [{"evidence_level": "P1_real_tensor_bytes"}]
        p2 = [{"evidence_level": "P2_real_comm_bucket"}]
        p3 = [{"evidence_level": "P3_artifact_payload"}]

        self.assertEqual(
            trace_payload.claim_scope_from_evidence(p0)["claim_scope"],
            "analytical_sensitivity_only",
        )
        self.assertEqual(
            trace_payload.claim_scope_from_evidence(p1)["claim_scope"],
            "tensor_payload_plausibility",
        )
        self.assertEqual(
            trace_payload.claim_scope_from_evidence(p2)["claim_scope"],
            "real_communication_payload_claim_allowed",
        )
        self.assertEqual(
            trace_payload.claim_scope_from_evidence(p3)["claim_scope"],
            "real_communication_payload_claim_allowed",
        )

    def test_literature_profiles_separate_netzip_note_from_ratio_profiles(self):
        profile_path = RX_ROOT / "data" / "p0_literature_profiles.json"

        payload = json.loads(profile_path.read_text(encoding="utf-8"))

        usable_sources = {item["payload_source"] for item in payload["usable_ratio_profiles"]}
        deferred_sources = {item["source"] for item in payload["deferred_sources"]}
        self.assertIn("ebpc_alexnet_literature", usable_sources)
        self.assertIn("quad_e4m3_literature", usable_sources)
        self.assertIn("netzip_public_summary", deferred_sources)
        self.assertNotIn("netzip_public_summary", usable_sources)

    @unittest.skipIf(shutil.which("lz4") is None, "lz4 CLI is not installed")
    def test_lz4_measurement_builds_p1_profile_for_real_input_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            payload_path = Path(tmpdir) / "tensor_payload.bin"
            payload_path.write_bytes((b"\x00" * 4096) + (b"\x7f" * 4096))

            profile = lz4_measure.build_lz4_profile(
                payload_path,
                payload_source="local_tensor_payload.bin",
                evidence_level="P1_real_tensor_bytes",
                dtype="uint8",
                tensor_role="checkpoint",
                chunk_size=4096,
                lz4_path=shutil.which("lz4"),
            )

        self.assertEqual(profile["codec_family"], "lz4")
        self.assertEqual(profile["payload_realism"], "real_tensor_bytes")
        self.assertEqual(profile["original_bytes"], 8192)
        self.assertLess(profile["compressed_bytes"], profile["original_bytes"])
        self.assertIn("lz4", profile["provenance"])

    @unittest.skipIf(shutil.which("lz4") is None, "lz4 CLI is not installed")
    def test_lz4_measurement_rejects_synthetic_payload_marked_as_real(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            payload_path = Path(tmpdir) / "synthetic_payload.bin"
            payload_path.write_bytes(b"\x00" * 4096)

            with self.assertRaisesRegex(trace_payload.ProvenanceError, "synthetic"):
                lz4_measure.build_lz4_profile(
                    payload_path,
                    payload_source="synthetic_zero_tensor",
                    evidence_level="P1_real_tensor_bytes",
                    dtype="uint8",
                    tensor_role="generated_synthetic_tensor",
                    chunk_size=4096,
                    lz4_path=shutil.which("lz4"),
                )

    def test_ddp_capture_profile_checks_bucket_size_and_marks_p2(self):
        bucket = ddp_capture.BytesGradBucket(b"\x01\x02\x03\x04" * 1024)

        profile = ddp_capture.profile_grad_bucket_bytes(
            bucket,
            payload_source="ddp_rank0_bucket7_step3",
            codec_family="raw_capture",
            compressed_bytes=2048,
            dtype="fp16",
            tensor_role="gradient_bucket",
            chunk_size=4096,
            provenance="captured through GradBucket.buffer() during DDP backward pass",
        )

        self.assertEqual(profile["evidence_level"], "P2_real_comm_bucket")
        self.assertEqual(profile["original_bytes"], 4096)
        self.assertEqual(profile["ratio"], 2.0)
        self.assertEqual(profile["payload_realism"], "real_comm_bucket")

    def test_ddp_capture_rejects_mismatched_recorded_bucket_size(self):
        bucket = ddp_capture.BytesGradBucket(b"\x01\x02\x03\x04")

        with self.assertRaisesRegex(trace_payload.ProvenanceError, "bucket size"):
            ddp_capture.profile_grad_bucket_bytes(
                bucket,
                payload_source="ddp_rank0_bucket7_step3",
                codec_family="raw_capture",
                compressed_bytes=2,
                dtype="fp16",
                tensor_role="gradient_bucket",
                chunk_size=4096,
                provenance="captured through GradBucket.buffer() during DDP backward pass",
                recorded_original_bytes=8,
            )


if __name__ == "__main__":
    unittest.main()
