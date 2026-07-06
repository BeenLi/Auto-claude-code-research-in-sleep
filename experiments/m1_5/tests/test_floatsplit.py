"""TDD for the float-split / bit-plane transform (M1.5).

The transform reorders the bits of a float KV byte stream so a byte codec can see
the low-entropy exponent structure separately from the high-entropy mantissa. The
non-negotiable property is BIT-EXACT reversibility: the WR-ZipGuard receiver must
reconstruct the original KV after commodity BF3 deflate-decompresses the transformed
stream, so any transform here must invert perfectly for every dtype.
"""

import numpy as np
import ml_dtypes
import pytest

import floatsplit as fs


_DTYPE_OBJ = {
    "bf16": ml_dtypes.bfloat16,
    "fp8_e4m3": ml_dtypes.float8_e4m3fn,
    "fp8_e5m2": ml_dtypes.float8_e5m2,
}


def _real_kv_bytes(dtype: str, n: int = 5000, seed: int = 7) -> bytes:
    rng = np.random.default_rng(seed)
    vals = rng.standard_normal(n).astype(_DTYPE_OBJ[dtype])
    return vals.tobytes()


def test_bitplane_roundtrip_bf16_is_bit_exact():
    buf = _real_kv_bytes("bf16")
    n = fs.n_values(buf, "bf16")
    blob = fs.transform(buf, "bf16", "bitplane")
    back = fs.invert(blob, "bf16", "bitplane", n)
    assert back == buf


def test_byte_transpose_roundtrip_bf16_actually_reorders():
    buf = _real_kv_bytes("bf16")
    n = fs.n_values(buf, "bf16")
    blob = fs.transform(buf, "bf16", "byte_transpose")
    assert len(blob) == len(buf)
    assert blob != buf  # a 2-byte dtype must genuinely permute
    back = fs.invert(blob, "bf16", "byte_transpose", n)
    assert back == buf


def test_byte_transpose_is_noop_for_one_byte_fp8():
    buf = _real_kv_bytes("fp8_e5m2")
    blob = fs.transform(buf, "fp8_e5m2", "byte_transpose")
    assert blob == buf  # 1 byte per value: nothing to move


@pytest.mark.parametrize("dtype", ["bf16", "fp8_e4m3", "fp8_e5m2"])
@pytest.mark.parametrize("method", ["bitplane", "byte_transpose"])
@pytest.mark.parametrize("n", [1, 7, 4099, 5000])  # 4099/7 force non-byte-aligned bit packing
def test_roundtrip_all_dtypes_methods_lengths(dtype, method, n):
    buf = _real_kv_bytes(dtype, n=n)
    blob = fs.transform(buf, dtype, method)
    back = fs.invert(blob, dtype, method, fs.n_values(buf, dtype))
    assert back == buf


def test_split_fields_pins_bit_positions():
    # Self-consistent reversibility can't catch a sign<->exp mislabel; known floats can.
    import numpy as _np

    bf16 = _np.array([1.0, 2.0, -2.0, 0.5], dtype=_DTYPE_OBJ["bf16"]).tobytes()
    sign, exp, mant = fs.split_fields(bf16, "bf16")
    assert list(sign) == [0, 0, 1, 0]
    assert list(exp) == [127, 128, 128, 126]  # bias-127; 1.0->127, 2.0->128, 0.5->126
    assert list(mant) == [0, 0, 0, 0]

    e5m2 = _np.array([1.0, 2.0, -2.0, 0.5], dtype=_DTYPE_OBJ["fp8_e5m2"]).tobytes()
    s, e, m = fs.split_fields(e5m2, "fp8_e5m2")
    assert list(s) == [0, 0, 1, 0]
    assert list(e) == [15, 16, 16, 14]  # bias-15
    assert list(m) == [0, 0, 0, 0]

    e4m3 = _np.array([1.0, 2.0, -2.0, 0.5], dtype=_DTYPE_OBJ["fp8_e4m3"]).tobytes()
    s, e, m = fs.split_fields(e4m3, "fp8_e4m3")
    assert list(s) == [0, 0, 1, 0]
    assert list(e) == [7, 8, 8, 6]  # bias-7


def test_plane_sizes_match_bit_widths():
    n = 1000
    buf = _real_kv_bytes("fp8_e5m2", n=n)
    p = fs.split_planes(buf, "fp8_e5m2")
    assert len(p["sign"]) == (n * 1 + 7) // 8
    assert len(p["exp"]) == (n * 5 + 7) // 8
    assert len(p["mantissa"]) == (n * 2 + 7) // 8


def test_exponent_plane_is_lower_entropy_than_raw_stream():
    # The mechanism: clustered magnitudes => exponent plane is low-entropy, even though
    # the raw interleaved stream sits near its byte-entropy floor (the M1 finding).
    import entropy  # reused from experiments/m1 via conftest path shim

    buf = _real_kv_bytes("bf16", n=20000)
    raw_h = entropy.shannon_entropy_bits_per_byte(buf)
    exp_plane = fs.split_planes(buf, "bf16")["exp"]
    exp_h = entropy.shannon_entropy_bits_per_byte(exp_plane)
    assert exp_h < raw_h


def test_invert_rejects_wrong_length_blob():
    buf = _real_kv_bytes("bf16", n=100)
    blob = fs.transform(buf, "bf16", "bitplane")
    with pytest.raises(ValueError):
        fs.invert(blob + b"\x00", "bf16", "bitplane", 100)
