"""TDD for measure_transform: apply a float-split transform, deflate, report alpha.

measure_transform is the per-chunk measurement primitive. It compares the transformed
stream's compression against the raw-stream baseline (which reproduces M1), in two modes:
- concat: deflate the whole transformed buffer as ONE stream (faithful to BF3's single-
  stream hardware decompress) — the alpha WR-ZipGuard could claim end-to-end.
- per-plane (bitplane only): deflate sign+exp, store mantissa RAW (DietGPU-style ceiling).
It also reports the per-plane alphas (to expose the exponent-vs-mantissa mechanism) and the
sender-side transform throughput, and it asserts bit-exact reversibility of the transform.
"""

import numpy as np
import ml_dtypes
import pytest

import split_measure as sm
import synth
from synth import TensorSpec


_DTYPE_OBJ = {
    "bf16": ml_dtypes.bfloat16,
    "fp8_e4m3": ml_dtypes.float8_e4m3fn,
    "fp8_e5m2": ml_dtypes.float8_e5m2,
}


def _kv_chunk(dtype: str, seq_len: int = 1024) -> bytes:
    # Small but >256KB (representative of the BF3 min chunk) so tests stay fast.
    spec = TensorSpec(
        phase="prefill", tensor_type="K", dtype=dtype,
        num_heads=8, head_dim=64, seq_len=seq_len, layer_idx=0, seed=42,
    )
    return synth.to_bytes(synth.generate_kv_tensor(spec))


@pytest.mark.parametrize("dtype", ["bf16", "fp8_e4m3", "fp8_e5m2"])
@pytest.mark.parametrize("method", ["byte_transpose", "bitplane"])
def test_measure_transform_is_bit_exact_and_bounded(dtype, method):
    chunk = _kv_chunk(dtype)
    r = sm.measure_transform(chunk, dtype, method, level=6)
    assert r["bit_exact"] is True
    assert r["original_size"] == len(chunk)
    assert 0.0 < r["alpha_raw"] <= 1.05
    assert 0.0 < r["alpha_concat"] <= 1.05
    assert r["transform_throughput_mbps"] > 0.0


def test_bitplane_reports_per_plane_and_byte_transpose_does_not():
    chunk = _kv_chunk("bf16")
    bp = sm.measure_transform(chunk, "bf16", "bitplane", level=6)
    assert bp["perplane"] is not None
    # The mechanism: exponent plane compresses, mantissa plane is near-incompressible.
    assert bp["perplane"]["alpha_exp"] < 0.9
    assert bp["perplane"]["alpha_mant"] > 0.95

    bt = sm.measure_transform(chunk, "bf16", "byte_transpose", level=6)
    assert bt["perplane"] is None


def test_split_beats_raw_on_bf16_kv():
    # On bf16 KV (8 exponent bits diluting the stream), a split should drop below raw deflate.
    chunk = _kv_chunk("bf16")
    r = sm.measure_transform(chunk, "bf16", "byte_transpose", level=6)
    assert r["alpha_concat"] < r["alpha_raw"]
