"""TDD for the M1.5 sweep driver (synthetic corpus + row assembly).

Mirrors experiments/m1/run_corpus.py: the pure row assembly (build_split_row) and the
streaming sweep (run) are tested; the real-KV capture path is glue validated by running.
"""

import json
from pathlib import Path

import pytest

import run_split
from synth import TensorSpec


def _measurement():
    return {
        "dtype": "bf16", "method": "byte_transpose", "codec": "deflate", "level": 6,
        "original_size": 1024, "n_values": 512,
        "alpha_raw": 0.792, "alpha_concat": 0.701,
        "transform_throughput_mbps": 2400.0, "bit_exact": True,
        "perplane": None,
    }


def test_build_split_row_carries_metrics_and_computes_delta():
    spec = TensorSpec("prefill", "K", "bf16", 8, 64, 512, 0, 42)
    row = run_split.build_split_row(
        spec=spec, model_size="7b", chunk_size_bytes=1024,
        measurement=_measurement(), generation_method="synthetic", seed=42,
    )
    assert row["dtype"] == "bf16"
    assert row["method"] == "byte_transpose"
    assert row["alpha_raw"] == 0.792
    assert row["alpha_concat"] == 0.701
    # delta > 0 means the transform helped (raw alpha minus transformed alpha)
    assert abs(row["delta_vs_raw"] - (0.792 - 0.701)) < 1e-9
    assert row["generation_method"] == "synthetic"
    assert row["bit_exact"] is True


def test_run_synthetic_writes_rows_all_bit_exact(tmp_path):
    out = tmp_path / "m15_synth.jsonl"
    summary = run_split.run(
        out_path=out,
        models=["tiny"],
        dtypes=["bf16", "fp8_e5m2"],
        phases=["prefill"],
        tensor_types=["K"],
        seq_lens=[1024],
        layer_fracs=[0.0],
        chunk_sizes=[262144],
        methods=["byte_transpose", "bitplane"],
        seeds=[42],
        level=6,
        max_chunks_per_config=1,
    )
    assert summary["rows_written"] > 0
    assert summary["bit_exact_failures"] == 0
    rows = [json.loads(x) for x in Path(out).read_text().splitlines() if x.strip()]
    # every (dtype x method) combination present
    combos = {(r["dtype"], r["method"]) for r in rows}
    assert ("bf16", "byte_transpose") in combos
    assert ("bf16", "bitplane") in combos
    assert ("fp8_e5m2", "bitplane") in combos
    assert all(r["bit_exact"] for r in rows)
    # bf16 byte_transpose must record a real improvement over raw on synthetic KV
    bf = [r for r in rows if r["dtype"] == "bf16" and r["method"] == "byte_transpose"][0]
    assert bf["alpha_concat"] < bf["alpha_raw"]
