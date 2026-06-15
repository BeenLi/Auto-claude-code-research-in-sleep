"""Synthetic KV-cache tensor generation (M1_CHECKLIST §1.2.1, method A).

K tensors mimic the post-RoPE distribution (rotary modulation over a Gaussian
base); V tensors use a truncated normal. Output dtype is bf16 / fp8 via ml_dtypes,
so `to_bytes` yields exactly the on-wire KV byte layout.

This is the *primary* (breadth) corpus; its realism is cross-validated against HF
captures before the full sweep is trusted (see validate_overlap.py).
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

import ml_dtypes
import numpy as np

_DTYPES = {
    "bf16": ml_dtypes.bfloat16,
    "fp8_e4m3": ml_dtypes.float8_e4m3fn,
    "fp8_e5m2": ml_dtypes.float8_e5m2,
}


@dataclass
class TensorSpec:
    phase: str  # "prefill" | "decode"
    tensor_type: str  # "K" | "V"
    dtype: str  # key of _DTYPES
    num_heads: int
    head_dim: int
    seq_len: int
    layer_idx: int
    seed: int


def dtype_itemsize(dtype: str) -> int:
    if dtype not in _DTYPES:
        raise ValueError(f"unsupported dtype: {dtype}")
    return np.dtype(_DTYPES[dtype]).itemsize


def _seed_for(spec: TensorSpec) -> int:
    key = "|".join(
        str(x)
        for x in (
            spec.phase,
            spec.tensor_type,
            spec.dtype,
            spec.num_heads,
            spec.head_dim,
            spec.seq_len,
            spec.layer_idx,
            spec.seed,
        )
    )
    return int(hashlib.sha256(key.encode()).hexdigest()[:16], 16)


def _apply_rope(base: np.ndarray, seq_len: int) -> np.ndarray:
    # base: (seq, heads, head_dim) float32. Rotate the two head_dim halves.
    head_dim = base.shape[-1]
    half = head_dim // 2
    if half == 0:
        return base
    inv_freq = 1.0 / (10000.0 ** (np.arange(half) / half))
    ang = np.outer(np.arange(seq_len), inv_freq)  # (seq, half)
    cos = np.cos(ang)[:, None, :]
    sin = np.sin(ang)[:, None, :]
    x1 = base[..., :half]
    x2 = base[..., half : 2 * half]
    out = base.copy()
    out[..., :half] = x1 * cos - x2 * sin
    out[..., half : 2 * half] = x1 * sin + x2 * cos
    return out


def generate_kv_tensor(spec: TensorSpec) -> np.ndarray:
    if spec.dtype not in _DTYPES:
        raise ValueError(f"unsupported dtype: {spec.dtype}")
    rng = np.random.default_rng(_seed_for(spec))
    shape = (spec.seq_len, spec.num_heads, spec.head_dim)
    base = rng.standard_normal(shape, dtype=np.float32)
    if spec.tensor_type == "K":
        vals = _apply_rope(base, spec.seq_len)
    else:
        vals = np.clip(base, -3.0, 3.0)  # truncated normal for V
    return vals.astype(_DTYPES[spec.dtype])


def to_bytes(arr: np.ndarray) -> bytes:
    return arr.tobytes()
