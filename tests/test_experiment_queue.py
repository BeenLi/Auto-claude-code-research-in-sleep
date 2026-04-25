#!/usr/bin/env python3
"""Tests for the simulator-first experiment queue helpers."""

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools" / "experiment_queue"))

import build_manifest
import cosim_protocol
import queue_manager


class TestSimulatorManifestBuilder(unittest.TestCase):
    def test_preserves_simulator_fields_and_expands_grid(self):
        config = {
            "project": "rx_pressure",
            "backend": "cosim_gem5_htsim",
            "cwd": "/work/rx-pressure",
            "env": {"setup": "source env.sh"},
            "resources": {
                "slots": [
                    {"id": "sim0", "type": "cpu_sim"},
                    {"id": "sim1", "type": "cpu_sim"},
                ]
            },
            "cosim": {
                "coordinator": "external",
                "window_us": 100,
                "worker_lifecycle": "persistent_file_handshake",
                "htsim_variant": "broadcom_csg_htsim",
                "ground_truth": "rx_decompression_expansion_pressure",
            },
            "phases": [
                {
                    "name": "rx_pressure",
                    "grid": {"ratio": [1.5, 2.0]},
                    "template": {
                        "id": "rx_ratio_${ratio}",
                        "adapter": "cosim_gem5_htsim",
                        "cmd": "python3 run_cosim.py --ratio ${ratio}",
                        "resources": {"slot_type": "cpu_sim", "cpu_cores": 4},
                        "outputs": {
                            "required": [
                                "results/rx_ratio_${ratio}.json",
                                "exchange/cosim_trace.jsonl",
                            ]
                        },
                        "metrics": [
                            "rx_pressure",
                            "decompression_expansion_ratio",
                            "accepted_compressed_bytes",
                            "dropped_compressed_bytes",
                            "sender_retransmission_policy",
                        ],
                    },
                }
            ],
        }

        manifest = build_manifest.build(config)

        self.assertEqual(manifest["backend"], "cosim_gem5_htsim")
        self.assertEqual(manifest["env"]["setup"], "source env.sh")
        self.assertEqual(manifest["resources"]["slots"][0]["id"], "sim0")
        self.assertEqual(manifest["cosim"]["window_us"], 100)
        jobs = manifest["phases"][0]["jobs"]
        self.assertEqual([job["id"] for job in jobs], ["rx_ratio_1.5", "rx_ratio_2.0"])
        self.assertEqual(jobs[0]["adapter"], "cosim_gem5_htsim")
        self.assertEqual(jobs[0]["resources"]["slot_type"], "cpu_sim")
        self.assertIn("results/rx_ratio_1.5.json", jobs[0]["outputs"]["required"])
        self.assertIn("dropped_compressed_bytes", jobs[0]["metrics"])


class TestSimulatorQueueManager(unittest.TestCase):
    def test_assign_jobs_preserves_adapter_outputs_and_metrics(self):
        manifest = {
            "project": "rx_pressure",
            "phases": [
                {
                    "name": "sanity",
                    "jobs": [
                        {
                            "id": "gem5_rx_sanity",
                            "adapter": "gem5",
                            "cmd": "gem5.opt configs/rx.py",
                            "resources": {"slot_type": "cpu_sim"},
                            "outputs": {"required": ["results/gem5_rx_sanity.json"]},
                            "metrics": ["host_memory_write_gbps", "rx_stall_ns"],
                        }
                    ],
                }
            ],
        }
        state = queue_manager.load_state("/tmp/nonexistent-state.json", manifest)

        queue_manager.assign_jobs_to_phases(manifest, state)

        job = state["jobs"][0]
        self.assertEqual(job["adapter"], "gem5")
        self.assertEqual(job["outputs"]["required"], ["results/gem5_rx_sanity.json"])
        self.assertEqual(job["metrics"], ["host_memory_write_gbps", "rx_stall_ns"])
        self.assertIsNone(job["resource_slot"])

    def test_step_launches_against_generic_resource_slots_without_gpu_probe(self):
        manifest = {
            "project": "rx_pressure",
            "cwd": ".",
            "resources": {
                "slots": [
                    {"id": "sim0", "type": "cpu_sim"},
                    {"id": "sim1", "type": "cpu_sim"},
                ]
            },
            "max_parallel": 2,
            "phases": [
                {
                    "name": "sanity",
                    "jobs": [
                        {
                            "id": "job_a",
                            "adapter": "generic_shell",
                            "cmd": "echo a",
                            "resources": {"slot_type": "cpu_sim"},
                            "outputs": {"required": ["a.json"]},
                        },
                        {
                            "id": "job_b",
                            "adapter": "generic_shell",
                            "cmd": "echo b",
                            "resources": {"slot_type": "cpu_sim"},
                            "outputs": {"required": ["b.json"]},
                        },
                    ],
                }
            ],
        }
        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = os.path.join(tmpdir, "state.json")
            state = queue_manager.load_state(state_file, manifest)
            queue_manager.assign_jobs_to_phases(manifest, state)

            with patch.object(queue_manager, "free_gpus") as free_gpus, \
                 patch.object(queue_manager, "launch_job") as launch_job:
                launch_job.side_effect = [("EQ_job_a", 1001), ("EQ_job_b", 1002)]

                queue_manager.step(manifest, state, state_file, tmpdir)

            free_gpus.assert_not_called()
            running = [job for job in state["jobs"] if job["status"] == "running"]
            self.assertEqual(len(running), 2)
            self.assertEqual({job["resource_slot"] for job in running}, {"sim0", "sim1"})

    def test_failed_running_job_without_required_output_becomes_stuck(self):
        manifest = {
            "project": "rx_pressure",
            "cwd": ".",
            "resources": {"slots": [{"id": "sim0", "type": "cpu_sim"}]},
            "phases": [
                {
                    "name": "sanity",
                    "jobs": [
                        {
                            "id": "job_a",
                            "adapter": "generic_shell",
                            "cmd": "false",
                            "outputs": {"required": ["missing.json"]},
                        }
                    ],
                }
            ],
        }
        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = os.path.join(tmpdir, "state.json")
            state = queue_manager.load_state(state_file, manifest)
            queue_manager.assign_jobs_to_phases(manifest, state)
            state["jobs"][0].update(
                {
                    "status": "running",
                    "screen_name": "EQ_job_a",
                    "pid": None,
                    "resource_slot": "sim0",
                }
            )

            with patch.object(queue_manager, "screen_exists", return_value=False):
                queue_manager.step(manifest, state, state_file, tmpdir)

            self.assertEqual(state["jobs"][0]["status"], "stuck")
            self.assertTrue(queue_manager.all_done(state))


class TestCosimProtocol(unittest.TestCase):
    def test_initial_window_inputs_record_rx_pressure_ground_truth(self):
        inputs = cosim_protocol.build_window_inputs(
            run_id="rx_cosim",
            window_id=0,
            window_us=100,
            flows=[
                {
                    "flow_id": "f0",
                    "src": 0,
                    "dst": 1,
                    "compressed_bytes_arrived": 1024,
                    "raw_bytes_represented": 2048,
                    "compression_ratio": 2.0,
                }
            ],
        )

        self.assertEqual(inputs["gem5_input"]["scenario"], "rx_decompression_expansion_pressure")
        self.assertEqual(inputs["htsim_input"]["htsim_variant"], "broadcom_csg_htsim")
        self.assertEqual(inputs["htsim_input"]["rdma_semantics"]["network"], "lossy")
        self.assertEqual(inputs["htsim_input"]["rdma_semantics"]["completion"], "reliable")
        self.assertEqual(
            inputs["htsim_input"]["rdma_semantics"]["sender_retransmission_policy"],
            "rto",
        )
        self.assertEqual(inputs["gem5_input"]["time"]["end_ns"], 100_000)

    def test_rx_pressure_summary_requires_drop_and_retransmission_fields(self):
        gem5_output = {
            "rx_pressure": True,
            "rx_buffer_occupancy": 262144,
            "decompression_expansion_ratio": 2.0,
            "accepted_compressed_bytes": 98304,
            "dropped_compressed_bytes": 32768,
            "drop_reason": "rx_decompression_buffer_overflow",
            "host_memory_write_gbps": 420.5,
            "pcie_utilization": 0.81,
            "rx_stall_ns": 18000,
        }
        htsim_output = {
            "sender_retransmission_policy": "rto",
            "retransmitted_bytes": 32768,
            "goodput_bytes": 98304,
        }

        summary = cosim_protocol.summarize_rx_pressure_window(
            run_id="rx_cosim",
            window_id=12,
            gem5_output=gem5_output,
            htsim_output=htsim_output,
        )

        self.assertEqual(summary["metrics"]["dropped_compressed_bytes"], 32768)
        self.assertEqual(summary["metrics"]["sender_retransmission_policy"], "rto")
        self.assertEqual(summary["ground_truth"], cosim_protocol.RX_PRESSURE_GROUND_TRUTH)

    def test_rx_pressure_summary_rejects_lossless_only_outputs(self):
        with self.assertRaisesRegex(ValueError, "dropped_compressed_bytes"):
            cosim_protocol.summarize_rx_pressure_window(
                run_id="rx_cosim",
                window_id=1,
                gem5_output={
                    "rx_pressure": True,
                    "accepted_compressed_bytes": 1024,
                    "host_memory_write_gbps": 10.0,
                    "pcie_utilization": 0.2,
                    "rx_stall_ns": 0,
                },
                htsim_output={
                    "sender_retransmission_policy": "rto",
                    "retransmitted_bytes": 0,
                    "goodput_bytes": 1024,
                },
            )


if __name__ == "__main__":
    unittest.main()
