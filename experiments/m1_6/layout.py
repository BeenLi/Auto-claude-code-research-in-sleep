"""Channel-major layout transforms for M1.6 (TRACE-inspired), single-deflate-stream constrained.

TRACE (arXiv 2509.03377) reaches lossless bf16-KV alpha~0.53 with a channel-major
disaggregated bit-plane layout — in custom CXL-controller silicon. Its layout step,
though, is a pure permutation: real KV has per-channel scale structure (each head_dim
channel has a characteristic magnitude, hence a near-constant exponent) that the
token-major wire layout interleaves away. M1.6 measures how much of that gain survives
WR-ZipGuard's constraint that the receiver is a commodity BF3 doing ONE standard deflate
decompress: reorder channel-major, optionally byte-transpose and delta-code, then deflate
the whole buffer as a single stream.

Every transform here is size-preserving and exactly reversible with an off-GPU-feasible
inverse (strided copy and/or prefix sum); `inverse_cost_class` reports which, so the
profitability model can price the receive side. See
refine-logs/EVALUATION_CONTRACT_M1.6.md for the pre-registered criteria.
"""

from __future__ import annotations

import numpy as np

import floatsplit as fs

METHODS = ("byte_transpose", "chan", "chan_bt", "chan_bt_delta", "bt_delta", "delta")

_COST_CLASS = {
    "byte_transpose": "permutation",
    "chan": "permutation",
    "chan_bt": "permutation",
    "chan_bt_delta": "permutation+prefix_sum",
    "bt_delta": "permutation+prefix_sum",
    "delta": "prefix_sum",
}


def itemsize(dtype: str) -> int:
    return fs.LAYOUT[dtype][3]


def inverse_cost_class(method: str) -> str:
    return _COST_CLASS[method]


def _as_values(buf: bytes, dtype: str) -> np.ndarray:
    dt = np.dtype("<u2") if itemsize(dtype) == 2 else np.dtype(np.uint8)
    return np.frombuffer(buf, dtype=dt)


def channel_major(buf: bytes, dtype: str, *, head_dim: int) -> bytes:
    """(rows, head_dim) -> (head_dim, rows), element-wise: each channel becomes contiguous."""
    v = _as_values(buf, dtype)
    if head_dim <= 0 or v.size % head_dim:
        raise ValueError(f"{v.size} values not divisible by head_dim {head_dim}")
    return np.ascontiguousarray(v.reshape(-1, head_dim).T).tobytes()


def channel_major_inverse(blob: bytes, dtype: str, *, head_dim: int) -> bytes:
    v = _as_values(blob, dtype)
    if head_dim <= 0 or v.size % head_dim:
        raise ValueError(f"{v.size} values not divisible by head_dim {head_dim}")
    return np.ascontiguousarray(v.reshape(head_dim, -1).T).tobytes()


def byte_delta(buf: bytes) -> bytes:
    """Global byte-wise delta, mod 256. First byte kept verbatim."""
    u8 = np.frombuffer(buf, dtype=np.uint8)
    out = np.empty_like(u8)
    out[0] = u8[0]
    np.subtract(u8[1:], u8[:-1], out=out[1:])  # uint8 arithmetic wraps mod 256
    return out.tobytes()


def byte_delta_inverse(blob: bytes) -> bytes:
    d = np.frombuffer(blob, dtype=np.uint8)
    return (np.cumsum(d, dtype=np.uint64) % 256).astype(np.uint8).tobytes()


def transform(buf: bytes, dtype: str, method: str, *, head_dim: int) -> bytes:
    """Apply ``method``; the result is compressed as ONE standard deflate stream."""
    if method == "byte_transpose":
        return fs.transform(buf, dtype, "byte_transpose")
    if method == "chan":
        return channel_major(buf, dtype, head_dim=head_dim)
    if method == "chan_bt":
        return fs.byte_transpose(channel_major(buf, dtype, head_dim=head_dim), dtype)
    if method == "chan_bt_delta":
        return byte_delta(fs.byte_transpose(channel_major(buf, dtype, head_dim=head_dim), dtype))
    if method == "bt_delta":
        return byte_delta(fs.byte_transpose(buf, dtype))
    if method == "delta":
        return byte_delta(buf)
    raise ValueError(f"unknown transform method: {method}")


def invert(blob: bytes, dtype: str, method: str, n: int, *, head_dim: int) -> bytes:
    if method == "byte_transpose":
        return fs.invert(blob, dtype, "byte_transpose", n)
    if method == "chan":
        return channel_major_inverse(blob, dtype, head_dim=head_dim)
    if method == "chan_bt":
        return channel_major_inverse(fs.byte_transpose_inverse(blob, dtype), dtype, head_dim=head_dim)
    if method == "chan_bt_delta":
        return channel_major_inverse(
            fs.byte_transpose_inverse(byte_delta_inverse(blob), dtype), dtype, head_dim=head_dim
        )
    if method == "bt_delta":
        return fs.byte_transpose_inverse(byte_delta_inverse(blob), dtype)
    if method == "delta":
        return byte_delta_inverse(blob)
    raise ValueError(f"unknown transform method: {method}")
