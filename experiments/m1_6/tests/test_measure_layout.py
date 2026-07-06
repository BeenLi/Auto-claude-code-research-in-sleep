"""Tests for M1.6 per-chunk measurement (measure_layout.py)."""

import zlib

import numpy as np
import pytest

import layout
import measure_layout


def _chunk(dtype: str, n_rows: int = 2048, head_dim: int = 64, seed: int = 0) -> bytes:
    rng = np.random.default_rng(seed)
    scale = np.exp2(np.arange(head_dim) % 8).astype(np.float32)
    vals = (rng.standard_normal((n_rows, head_dim)).astype(np.float32) * scale)
    if dtype == "bf16":
        return ((vals.view(np.uint32) >> 16).astype("<u2")).tobytes()
    # fp8: just use the low byte of the bf16 pattern as a stand-in byte stream
    return ((vals.view(np.uint32) >> 16).astype("<u2") & 0xFF).astype(np.uint8).tobytes()


def test_measure_returns_expected_fields_and_bit_exact():
    chunk = _chunk("bf16")
    m = measure_layout.measure(chunk, "bf16", "chan_bt", head_dim=64, warmup=0, repeats=1)
    for k in ("dtype", "method", "codec", "level", "original_size", "n_values",
              "alpha_raw", "alpha_concat", "transform_throughput_mbps", "bit_exact",
              "inverse_cost_class", "head_dim"):
        assert k in m, k
    assert m["bit_exact"] is True
    assert m["inverse_cost_class"] == "permutation"
    assert m["head_dim"] == 64
    assert 0 < m["alpha_concat"] <= 1.2
    assert 0 < m["alpha_raw"] <= 1.2


def test_measure_alpha_concat_matches_manual_zlib():
    chunk = _chunk("bf16", seed=3)
    m = measure_layout.measure(chunk, "bf16", "chan", head_dim=64, warmup=0, repeats=1)
    manual = len(zlib.compress(layout.transform(chunk, "bf16", "chan", head_dim=64), 6)) / len(chunk)
    assert abs(m["alpha_concat"] - manual) < 1e-12


def test_measure_routes_m15_methods_too():
    chunk = _chunk("bf16", seed=4)
    m = measure_layout.measure(chunk, "bf16", "byte_transpose", head_dim=64, warmup=0, repeats=1)
    assert m["bit_exact"] is True


def test_measure_rejects_empty_chunk():
    with pytest.raises(ValueError):
        measure_layout.measure(b"", "bf16", "chan", head_dim=64)
