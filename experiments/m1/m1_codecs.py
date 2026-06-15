"""Lossless codec matrix for M1 compressibility measurement.

BF3 hardware decompresses deflate and lz4 (DOCA Compress); zstd/snappy are
software-only reference baselines. `measure` runs warmup + timed repeats, computes
the compression ratio and throughput, and verifies a bit-exact roundtrip.

Named m1_codecs to avoid shadowing the stdlib `codecs` module on sys.path.
"""

from __future__ import annotations

import time
import zlib
from dataclasses import dataclass

import lz4.frame
import zstandard

_REPRESENTATIVE_LEVELS = {
    "deflate": [1, 6, 9],
    "lz4": [0, 9],
    "zstd": [1, 3, 19],
    "snappy": [None],
    "none": [None],
}


def _has_snappy() -> bool:
    try:
        import snappy  # noqa: F401

        return True
    except Exception:
        return False


def available_codecs() -> list[str]:
    names = ["none", "deflate", "lz4", "zstd"]
    if _has_snappy():
        names.append("snappy")
    return names


def codec_levels(codec: str) -> list:
    if codec not in _REPRESENTATIVE_LEVELS:
        raise ValueError(f"unknown codec: {codec}")
    return list(_REPRESENTATIVE_LEVELS[codec])


def compress(data: bytes, codec: str, level=None) -> bytes:
    if codec == "none":
        return data
    if codec == "deflate":
        return zlib.compress(data, 6 if level is None else level)
    if codec == "lz4":
        return lz4.frame.compress(data, compression_level=0 if level is None else level)
    if codec == "zstd":
        return zstandard.ZstdCompressor(level=3 if level is None else level).compress(data)
    if codec == "snappy":
        import snappy

        return snappy.compress(data)
    raise ValueError(f"unknown codec: {codec}")


def decompress(blob: bytes, codec: str, level=None) -> bytes:
    if codec == "none":
        return blob
    if codec == "deflate":
        return zlib.decompress(blob)
    if codec == "lz4":
        return lz4.frame.decompress(blob)
    if codec == "zstd":
        return zstandard.ZstdDecompressor().decompress(blob)
    if codec == "snappy":
        import snappy

        return snappy.decompress(blob)
    raise ValueError(f"unknown codec: {codec}")


@dataclass
class Measurement:
    codec: str
    level: object
    original_size: int
    compressed_size: int
    ratio: float
    compress_time_s: float
    compress_throughput_mbps: float
    is_bit_exact: bool


def measure(data: bytes, codec: str, level=None, *, warmup: int = 2, repeats: int = 5) -> Measurement:
    if codec not in available_codecs():
        raise ValueError(f"unknown or unavailable codec: {codec}")

    for _ in range(warmup):
        compress(data, codec, level)

    times: list[int] = []
    blob = b""
    for _ in range(max(1, repeats)):
        t0 = time.perf_counter_ns()
        blob = compress(data, codec, level)
        times.append(time.perf_counter_ns() - t0)
    times.sort()
    p50_ns = times[len(times) // 2]
    t_s = max(p50_ns, 1) / 1e9  # guard zero-time on tiny inputs

    original = len(data)
    compressed = len(blob)
    throughput_mbps = (original / 1e6) / t_s
    is_bit_exact = decompress(blob, codec, level) == data

    return Measurement(
        codec=codec,
        level=level,
        original_size=original,
        compressed_size=compressed,
        ratio=compressed / original if original else 1.0,
        compress_time_s=t_s,
        compress_throughput_mbps=throughput_mbps,
        is_bit_exact=is_bit_exact,
    )
