"""Float-split / bit-plane reversible transforms for M1.5.

WR-ZipGuard's M1 measured deflate on the *raw, interleaved* KV byte stream and hit
the order-0 byte-entropy floor (bf16 ~0.79, fp8_e5m2 ~0.73). Papers like DietGPU /
UCCL-Zip / NetZIP apply a layout transform *before* compression so a byte codec can
isolate the low-entropy exponent from the near-random mantissa. This module provides
those transforms — and, critically, their exact inverses, since WR-ZipGuard's receiver
must reconstruct the original KV bit-for-bit after commodity BF3 deflate-decompresses
the transformed stream.

Two transforms:
- ``byte_transpose`` — Structure-of-Arrays byte permutation. For a 2-byte dtype (bf16)
  it groups the sign+high-exponent bytes apart from the exp-lsb+mantissa bytes. It is a
  pure permutation (FPGA-cheap) but a NO-OP for 1-byte dtypes (fp8), since there is only
  one byte per value to move.
- ``bitplane`` — exact sign/exponent/mantissa field split, bit-packed into three
  contiguous planes. Works for every dtype including fp8 (the only way to expose fp8's
  sub-byte exponent), at the cost of a sub-byte gather on both ends.

Layout note (verified against ml_dtypes, little-endian x86): for bf16 the 2-byte value
V = (sign<<15) | (exp<<7) | mantissa, so byte0 (low, in memory) is exp-lsb+mantissa
(high entropy) and byte1 (high) is sign+exp (low entropy). A naive "first byte is the
exponent" assumption is wrong on little-endian — hence the explicit field math here.
"""

from __future__ import annotations

import numpy as np

# (sign_bits, exp_bits, mantissa_bits, itemsize_bytes)
LAYOUT = {
    "bf16": (1, 8, 7, 2),
    "fp8_e4m3": (1, 4, 3, 1),
    "fp8_e5m2": (1, 5, 2, 1),
}

TRANSFORMS = ("byte_transpose", "bitplane")


def _layout(dtype: str):
    if dtype not in LAYOUT:
        raise ValueError(f"unsupported dtype: {dtype}")
    return LAYOUT[dtype]


def n_values(buf: bytes, dtype: str) -> int:
    _, _, _, itemsize = _layout(dtype)
    if len(buf) % itemsize:
        raise ValueError(f"buffer length {len(buf)} not a multiple of itemsize {itemsize}")
    return len(buf) // itemsize


def _as_uint(buf: bytes, itemsize: int) -> np.ndarray:
    dt = np.dtype("<u2") if itemsize == 2 else np.dtype(np.uint8)
    return np.frombuffer(buf, dtype=dt)


def split_fields(buf: bytes, dtype: str):
    """Return (sign, exp, mantissa) as uint arrays, one entry per value."""
    sign_bits, exp_bits, mant_bits, itemsize = _layout(dtype)
    v = _as_uint(buf, itemsize).astype(np.uint32)
    mant_mask = (1 << mant_bits) - 1
    exp_mask = (1 << exp_bits) - 1
    mantissa = v & mant_mask
    exp = (v >> mant_bits) & exp_mask
    sign = (v >> (mant_bits + exp_bits)) & ((1 << sign_bits) - 1)
    return sign, exp, mantissa


def _pack_field(vals: np.ndarray, width: int) -> bytes:
    """Bit-pack one integer field (``width`` bits each, MSB-first) across all values."""
    if width == 0:
        return b""
    shifts = np.arange(width - 1, -1, -1, dtype=np.uint32)
    bitmat = ((vals[:, None] >> shifts) & 1).astype(np.uint8)  # (N, width), MSB-first
    return np.packbits(bitmat.reshape(-1)).tobytes()


def _unpack_field(blob: bytes, width: int, n: int) -> np.ndarray:
    if width == 0:
        return np.zeros(n, dtype=np.uint32)
    bits = np.unpackbits(np.frombuffer(blob, dtype=np.uint8))[: n * width].reshape(n, width)
    weights = (1 << np.arange(width - 1, -1, -1, dtype=np.uint32))
    return (bits.astype(np.uint32) * weights).sum(axis=1)


def _plane_nbytes(n: int, width: int) -> int:
    return (n * width + 7) // 8


def split_planes(buf: bytes, dtype: str) -> dict:
    """Bit-packed sign/exp/mantissa planes (each a contiguous byte stream)."""
    sign_bits, exp_bits, mant_bits, _ = _layout(dtype)
    sign, exp, mantissa = split_fields(buf, dtype)
    return {
        "sign": _pack_field(sign, sign_bits),
        "exp": _pack_field(exp, exp_bits),
        "mantissa": _pack_field(mantissa, mant_bits),
    }


def join_planes(planes: dict, dtype: str, n: int) -> bytes:
    """Inverse of split_planes: reconstruct the original little-endian byte stream."""
    sign_bits, exp_bits, mant_bits, itemsize = _layout(dtype)
    sign = _unpack_field(planes["sign"], sign_bits, n)
    exp = _unpack_field(planes["exp"], exp_bits, n)
    mantissa = _unpack_field(planes["mantissa"], mant_bits, n)
    v = (sign << (mant_bits + exp_bits)) | (exp << mant_bits) | mantissa
    out_dt = np.dtype("<u2") if itemsize == 2 else np.dtype(np.uint8)
    return v.astype(out_dt).tobytes()


def transform(buf: bytes, dtype: str, method: str) -> bytes:
    """Apply ``method`` and return a single concatenated byte stream (one deflate input)."""
    if method == "bitplane":
        p = split_planes(buf, dtype)
        return p["sign"] + p["exp"] + p["mantissa"]
    if method == "byte_transpose":
        return byte_transpose(buf, dtype)
    raise ValueError(f"unknown transform method: {method}")


def invert(blob: bytes, dtype: str, method: str, n: int) -> bytes:
    if method == "bitplane":
        sign_bits, exp_bits, mant_bits, _ = _layout(dtype)
        s_n = _plane_nbytes(n, sign_bits)
        e_n = _plane_nbytes(n, exp_bits)
        m_n = _plane_nbytes(n, mant_bits)
        if len(blob) != s_n + e_n + m_n:
            raise ValueError(f"bitplane blob length {len(blob)} != expected {s_n + e_n + m_n}")
        planes = {
            "sign": blob[:s_n],
            "exp": blob[s_n : s_n + e_n],
            "mantissa": blob[s_n + e_n :],
        }
        return join_planes(planes, dtype, n)
    if method == "byte_transpose":
        return byte_transpose_inverse(blob, dtype)
    raise ValueError(f"unknown transform method: {method}")


def byte_transpose(buf: bytes, dtype: str) -> bytes:
    """Structure-of-Arrays byte permutation; identity for 1-byte dtypes."""
    _, _, _, itemsize = _layout(dtype)
    if itemsize == 1:
        return buf
    n = n_values(buf, dtype)
    u8 = np.frombuffer(buf, dtype=np.uint8).reshape(n, itemsize)
    return np.ascontiguousarray(u8.T).tobytes()  # plane 0 (all byte0), then plane 1, ...


def byte_transpose_inverse(blob: bytes, dtype: str) -> bytes:
    _, _, _, itemsize = _layout(dtype)
    if itemsize == 1:
        return blob
    if len(blob) % itemsize:
        raise ValueError(f"buffer length {len(blob)} not a multiple of itemsize {itemsize}")
    n = len(blob) // itemsize
    planes = np.frombuffer(blob, dtype=np.uint8).reshape(itemsize, n)
    return np.ascontiguousarray(planes.T).tobytes()
