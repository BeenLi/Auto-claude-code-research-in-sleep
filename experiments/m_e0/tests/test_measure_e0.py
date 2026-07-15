"""Per-chunk E0 measurement: one transform, all six codec variants, bit-exact gates."""

import numpy as np
import pytest

import e0_codecs
import measure_e0
import synth
from synth import TensorSpec


def _chunk(dtype: str, head_dim: int = 64, seq_len: int = 512) -> bytes:
    spec = TensorSpec("prefill", "K", dtype, 8, head_dim, seq_len, 0, 42)
    return synth.to_bytes(synth.generate_kv_tensor(spec))[: 256 * 1024]


class TestMeasure:
    def test_raw_method_reports_all_variants(self):
        chunk = _chunk("bf16")
        row = measure_e0.measure(chunk, "bf16", "raw", head_dim=64)
        assert set(row["alphas"]) == set(e0_codecs.VARIANTS)
        assert row["bit_exact"] is True
        assert row["method"] == "raw"
        assert row["original_size"] == len(chunk)

    def test_raw_v0_matches_e0_codecs_alpha(self):
        chunk = _chunk("bf16")
        row = measure_e0.measure(chunk, "bf16", "raw", head_dim=64)
        assert row["alphas"]["V0"] == pytest.approx(e0_codecs.alpha(chunk, "V0"))

    def test_byte_transpose_beats_raw_on_synth_bf16(self):
        # The locked M1.5 result: synthetic bf16 byte-transpose ~0.70 vs raw ~0.79.
        chunk = _chunk("bf16")
        raw = measure_e0.measure(chunk, "bf16", "raw", head_dim=64)
        bt = measure_e0.measure(chunk, "bf16", "byte_transpose", head_dim=64)
        assert bt["alphas"]["V0"] < raw["alphas"]["V0"] - 0.02

    def test_transform_bit_exactness_gates_row(self):
        chunk = _chunk("fp8_e5m2")
        row = measure_e0.measure(chunk, "fp8_e5m2", "chan", head_dim=64)
        assert row["bit_exact"] is True

    def test_static_huffman_never_beats_dynamic_same_shape(self):
        chunk = _chunk("bf16")
        row = measure_e0.measure(chunk, "bf16", "byte_transpose", head_dim=64)
        assert row["alphas"]["V4"] >= row["alphas"]["V3"] - 1e-9
