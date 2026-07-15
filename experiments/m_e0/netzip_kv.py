"""NetZIP-algorithm (MICRO'25) ported to WR-ZipGuard's KV corpus — E0b positioning arm.

Faithful numpy/ml_dtypes reimplementation of the Zenodo artifact's
`compression_ratio_calculation.py` (github.com/ece-fast-lab/MICRO-2025-NetZIP, MIT):

- ``bit_group``   = bit_group_bfloat16: 16 bit-planes, packbits(bitorder="little").
- ``byte_group``  = byte_group_bfloat16: low bytes then high bytes (2-byte SoA
  de-interleave — mechanically identical to our M1.5 byte_transpose).
- ``diff_min``    = difference_encode_bfloat16 with a 1st-percentile base
  (float32 subtract, re-cast to bf16 — NOT exactly invertible in general; ratio-only
  arm, no bit-exact claim).

Declared adaptations (EVALUATION_CONTRACT_E0.md, E0b): cross-iteration diff arms are
N/A for KV (no previous training step); the min base is the SAME buffer's 1st
percentile (their base comes from the previous step's tensor). Their compressor
defaults are level-1 lz4/snappy/zlib/zstd; zlib-6 is added for comparability with our
locked α. bf16 only — the artifact's groupers are 2-byte-specific (the paper concedes
byte-grouping is ineffective for 8-bit formats).
"""

from __future__ import annotations

import zlib

import ml_dtypes
import numpy as np

ARMS = (
    "original",
    "bit_grouped",
    "byte_grouped",
    "diff_min_encoded",
    "diff_min_bit_grouped",
    "diff_min_byte_grouped",
)


def _as_i16(data: bytes) -> np.ndarray:
    return np.frombuffer(data, dtype="<i2")


def byte_group(data: bytes) -> bytes:
    arr_bytes = np.frombuffer(data, dtype=np.uint8).reshape(-1, 2)
    return np.concatenate([arr_bytes[:, 0], arr_bytes[:, 1]]).tobytes()


def bit_group(data: bytes) -> bytes:
    arr = _as_i16(data)
    bits = (arr[:, None] >> np.arange(16)) & 1
    packed = np.packbits(bits.transpose().astype(np.uint8), axis=1, bitorder="little")
    return packed.reshape(-1).tobytes()


def min_base(data: bytes) -> float:
    vals = np.frombuffer(data, dtype=ml_dtypes.bfloat16).astype(np.float32)
    return float(np.percentile(vals, 1))


def diff_min(data: bytes) -> bytes:
    base = min_base(data)
    vals = np.frombuffer(data, dtype=ml_dtypes.bfloat16).astype(np.float32)
    return (vals - base).astype(ml_dtypes.bfloat16).tobytes()


def situations(data: bytes) -> dict[str, bytes]:
    d = diff_min(data)
    return {
        "original": data,
        "bit_grouped": bit_group(data),
        "byte_grouped": byte_group(data),
        "diff_min_encoded": d,
        "diff_min_bit_grouped": bit_group(d),
        "diff_min_byte_grouped": byte_group(d),
    }


def _codecs() -> dict[str, callable]:
    codecs = {
        "zlib-1": lambda b: zlib.compress(b, 1),
        "zlib-6": lambda b: zlib.compress(b, 6),
    }
    try:
        import lz4.frame

        codecs["lz4-1"] = lambda b: lz4.frame.compress(b, compression_level=1)
    except ImportError:
        pass
    try:
        import zstandard

        codecs["zstd-1"] = zstandard.ZstdCompressor(level=1).compress
    except ImportError:
        pass
    try:
        import snappy

        codecs["snappy"] = snappy.compress
    except ImportError:
        pass
    return codecs


def measure(data: bytes) -> list[dict]:
    rows = []
    for situation, buf in situations(data).items():
        for codec, fn in _codecs().items():
            rows.append(
                {
                    "situation": situation,
                    "codec": codec,
                    "original_size": len(data),
                    "compressed_size": len(fn(buf)),
                    "alpha": len(fn(buf)) / len(data),
                }
            )
    return rows
