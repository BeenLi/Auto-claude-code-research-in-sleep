"""E0b runner: row assembly (capture leg is glue, validated on the box)."""

import numpy as np

import run_netzip


def test_measure_chunk_rows_carry_context():
    import ml_dtypes

    rng = np.random.default_rng(3)
    chunk = rng.standard_normal(131072).astype(ml_dtypes.bfloat16).tobytes()
    rows = run_netzip.measure_chunk_rows(
        chunk=chunk, model_size="gpt2", phase="prefill", tensor_type="K",
        layer_idx=0, chunk_size_bytes=len(chunk),
    )
    assert len(rows) >= 6 * 2  # six arms x at least two codecs
    for r in rows:
        assert r["model_size"] == "gpt2"
        assert r["dtype"] == "bf16"
        assert r["generation_method"] == "captured"
        assert 0 < r["alpha"] < 2
    assert {"original", "byte_grouped", "diff_min_byte_grouped"} <= {r["situation"] for r in rows}
