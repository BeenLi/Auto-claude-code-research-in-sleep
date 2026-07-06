"""TDD for the M1.6 sweep driver (synthetic corpus + row assembly).

Mirrors experiments/m1_5/tests/test_run_split.py: pure row assembly (build_row) and the
streaming synthetic sweep (run) are tested; the real-KV capture path is glue validated by
running on the box.
"""

import json
from pathlib import Path

import run_m16
from synth import TensorSpec


def _measurement():
    return {
        "dtype": "bf16", "method": "chan_bt", "codec": "deflate", "level": 6,
        "original_size": 1024, "n_values": 512, "head_dim": 64,
        "alpha_raw": 0.792, "alpha_concat": 0.671,
        "transform_throughput_mbps": 1800.0, "bit_exact": True,
        "inverse_cost_class": "permutation",
    }


def test_build_row_carries_metrics_and_computes_delta():
    spec = TensorSpec("prefill", "K", "bf16", 8, 64, 512, 0, 42)
    row = run_m16.build_row(
        spec=spec, model_size="7b", chunk_size_bytes=1024,
        measurement=_measurement(), generation_method="synthetic", seed=42,
    )
    assert row["dtype"] == "bf16"
    assert row["method"] == "chan_bt"
    assert row["head_dim"] == 64
    assert row["inverse_cost_class"] == "permutation"
    assert abs(row["delta_vs_raw"] - (0.792 - 0.671)) < 1e-9
    assert row["bit_exact"] is True


def test_run_synthetic_writes_rows_all_bit_exact(tmp_path):
    out = tmp_path / "m16_synth.jsonl"
    summary = run_m16.run(
        out_path=out,
        models=["tiny"],
        dtypes=["bf16", "fp8_e5m2"],
        phases=["prefill"],
        tensor_types=["K"],
        seq_lens=[1024],
        layer_fracs=[0.0],
        chunk_sizes=[262144],
        methods=["byte_transpose", "chan_bt", "chan_bt_delta"],
        seeds=[42],
        level=6,
        max_chunks_per_config=1,
    )
    assert summary["rows_written"] > 0
    assert summary["bit_exact_failures"] == 0
    rows = [json.loads(x) for x in Path(out).read_text().splitlines() if x.strip()]
    combos = {(r["dtype"], r["method"]) for r in rows}
    assert ("bf16", "chan_bt") in combos
    assert ("fp8_e5m2", "chan_bt_delta") in combos
    assert all(r["bit_exact"] for r in rows)
    assert all(r["head_dim"] > 0 for r in rows)
