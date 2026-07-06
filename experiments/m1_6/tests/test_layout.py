"""Tests for M1.6 channel-major layout transforms (layout.py).

Every transform must be bit-exact reversible (the receiver reconstructs KV after one
standard BF3 deflate decompress), and the channel-major mechanism must demonstrably
expose per-channel exponent structure that byte_transpose alone interleaves away.
"""

import zlib

import numpy as np
import pytest

import layout

DTYPES = ("bf16", "fp8_e4m3", "fp8_e5m2")
HEAD_DIMS = (64, 128)


def _rand_buf(dtype: str, n_rows: int, head_dim: int, seed: int = 0) -> bytes:
    itemsize = layout.itemsize(dtype)
    rng = np.random.default_rng(seed)
    return rng.integers(0, 256, size=n_rows * head_dim * itemsize, dtype=np.uint8).tobytes()


def _structured_bf16(n_rows: int, head_dim: int, seed: int = 1) -> bytes:
    """bf16 KV lookalike with per-channel scale structure: channel c has magnitude ~2^(c%8),
    so the exponent is ~constant within a channel but varies across channels — the structure
    channel-major reordering exists to exploit."""
    rng = np.random.default_rng(seed)
    scale = np.exp2(np.arange(head_dim) % 8).astype(np.float32)  # (head_dim,)
    vals = rng.standard_normal((n_rows, head_dim)).astype(np.float32) * scale
    f32 = vals.view(np.uint32)
    bf16 = (f32 >> 16).astype("<u2")  # truncate to bf16 bit pattern
    return bf16.tobytes()


# ---------------------------------------------------------------- channel_major

def test_channel_major_known_small_example_bf16():
    # 3 rows x head_dim 2, bf16: values are 2-byte units that must move atomically.
    # rows: [(a,b), (c,d), (e,f)]  ->  channel-major: [a,c,e, b,d,f]
    vals = np.array([[0x1122, 0x3344], [0x5566, 0x7788], [0x99AA, 0xBBCC]], dtype="<u2")
    buf = vals.tobytes()
    out = layout.channel_major(buf, "bf16", head_dim=2)
    expect = np.array([0x1122, 0x5566, 0x99AA, 0x3344, 0x7788, 0xBBCC], dtype="<u2").tobytes()
    assert out == expect


def test_channel_major_known_small_example_fp8():
    vals = np.array([[1, 2, 3], [4, 5, 6]], dtype=np.uint8)  # 2 rows x head_dim 3
    out = layout.channel_major(vals.tobytes(), "fp8_e5m2", head_dim=3)
    assert out == bytes([1, 4, 2, 5, 3, 6])


@pytest.mark.parametrize("dtype", DTYPES)
@pytest.mark.parametrize("head_dim", HEAD_DIMS)
def test_channel_major_roundtrip(dtype, head_dim):
    buf = _rand_buf(dtype, n_rows=257, head_dim=head_dim)
    fwd = layout.channel_major(buf, dtype, head_dim=head_dim)
    assert len(fwd) == len(buf)
    assert layout.channel_major_inverse(fwd, dtype, head_dim=head_dim) == buf


def test_channel_major_rejects_misaligned_buffer():
    buf = b"\x00" * (64 * 2 + 2)  # not a multiple of head_dim*itemsize rows
    with pytest.raises(ValueError):
        layout.channel_major(buf, "bf16", head_dim=64)


# ---------------------------------------------------------------- byte_delta

def test_byte_delta_wraparound_roundtrip():
    buf = bytes([5, 3, 250, 0, 255, 1])
    d = layout.byte_delta(buf)
    assert d[0] == 5 and d[1] == (3 - 5) % 256 and d[2] == (250 - 3) % 256
    assert layout.byte_delta_inverse(d) == buf


def test_byte_delta_roundtrip_random():
    buf = _rand_buf("fp8_e5m2", 512, 64, seed=7)
    assert layout.byte_delta_inverse(layout.byte_delta(buf)) == buf


def test_byte_delta_constant_stream_becomes_zeros():
    buf = bytes([42] * 1000)
    d = layout.byte_delta(buf)
    assert d[0] == 42 and set(d[1:]) == {0}


# ---------------------------------------------------------------- registry

def test_methods_registry_contents():
    assert set(layout.METHODS) == {
        "byte_transpose", "chan", "chan_bt", "chan_bt_delta", "bt_delta", "delta",
    }


@pytest.mark.parametrize("method", ["chan", "chan_bt", "chan_bt_delta", "bt_delta", "delta", "byte_transpose"])
@pytest.mark.parametrize("dtype", DTYPES)
@pytest.mark.parametrize("head_dim", HEAD_DIMS)
def test_transform_invert_bit_exact(method, dtype, head_dim):
    buf = _rand_buf(dtype, n_rows=128, head_dim=head_dim, seed=3)
    blob = layout.transform(buf, dtype, method, head_dim=head_dim)
    assert len(blob) == len(buf)  # all M1.6 transforms are size-preserving permut./delta
    n = len(buf) // layout.itemsize(dtype)
    assert layout.invert(blob, dtype, method, n, head_dim=head_dim) == buf


def test_transform_unknown_method_raises():
    with pytest.raises(ValueError):
        layout.transform(b"\x00\x00", "bf16", "nope", head_dim=1)


def test_chan_bt_is_composition():
    import floatsplit as fs
    buf = _structured_bf16(256, 64)
    manual = fs.byte_transpose(layout.channel_major(buf, "bf16", head_dim=64), "bf16")
    assert layout.transform(buf, "bf16", "chan_bt", head_dim=64) == manual


def test_chan_bt_equals_chan_for_1byte_dtypes():
    buf = _rand_buf("fp8_e5m2", 128, 64, seed=5)
    a = layout.transform(buf, "fp8_e5m2", "chan", head_dim=64)
    b = layout.transform(buf, "fp8_e5m2", "chan_bt", head_dim=64)
    assert a == b


def test_byte_transpose_passthrough_matches_floatsplit():
    import floatsplit as fs
    buf = _rand_buf("bf16", 128, 64, seed=6)
    assert layout.transform(buf, "bf16", "byte_transpose", head_dim=64) == fs.transform(buf, "bf16", "byte_transpose")


# ---------------------------------------------------------------- mechanism

def test_channel_major_exposes_per_channel_exponent_structure():
    """On data with per-channel scale structure, chan_bt(+delta) must deflate strictly
    better than byte_transpose alone — the core M1.6 mechanism."""
    buf = _structured_bf16(2048, 64)
    z = lambda b: len(zlib.compress(b, 6))
    bt = z(layout.transform(buf, "bf16", "byte_transpose", head_dim=64))
    chan_bt = z(layout.transform(buf, "bf16", "chan_bt", head_dim=64))
    chan_bt_delta = z(layout.transform(buf, "bf16", "chan_bt_delta", head_dim=64))
    assert chan_bt < bt
    assert min(chan_bt, chan_bt_delta) < bt


def test_inverse_cost_class_is_permutation_or_prefix_sum():
    """Contract disqualifier guard: every method must declare an off-GPU-feasible inverse
    class (permutation / prefix-sum), which the gate reports to the profitability model."""
    for m in layout.METHODS:
        assert layout.inverse_cost_class(m) in ("identity", "permutation", "prefix_sum", "permutation+prefix_sum")
