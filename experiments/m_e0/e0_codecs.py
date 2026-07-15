"""Hardware-encoder-proxy deflate variants for E0 (EVALUATION_CONTRACT_E0.md).

FPGA deflate encoders differ from software zlib -6 in match-search effort (~level 1),
Huffman coding (static vs dynamic), and block-level parallelism (independent 32 KB
blocks, no cross-block history). Each proxy here stays a standard RFC1950 zlib stream
— or, for the blocked variants, a concatenation of independent standard zlib streams —
so every measured alpha is still decodable by a stock decoder (and the M2-proven BF3
hardware path). Per-block container overhead is deliberately included in alpha.
"""

from __future__ import annotations

import zlib
from dataclasses import dataclass


@dataclass(frozen=True)
class Variant:
    level: int
    strategy: str  # "default" | "fixed"
    block_size: int | None  # None = one stream over the whole chunk


# Pre-registered variant table (contract "Scope and method").
VARIANTS: dict[str, Variant] = {
    "V0": Variant(level=6, strategy="default", block_size=None),
    "V1": Variant(level=1, strategy="default", block_size=None),
    "V2": Variant(level=6, strategy="default", block_size=32 * 1024),
    "V3": Variant(level=1, strategy="default", block_size=32 * 1024),
    "V4": Variant(level=1, strategy="fixed", block_size=32 * 1024),
    "V5": Variant(level=6, strategy="fixed", block_size=None),
}

_STRATEGIES = {"default": zlib.Z_DEFAULT_STRATEGY, "fixed": zlib.Z_FIXED}


def _compress_stream(data: bytes, level: int, strategy: str) -> bytes:
    co = zlib.compressobj(level, zlib.DEFLATED, 15, 8, _STRATEGIES[strategy])
    return co.compress(data) + co.flush()


def compress_variant(data: bytes, variant_id: str) -> bytes:
    v = VARIANTS[variant_id]
    if v.block_size is None:
        return _compress_stream(data, v.level, v.strategy)
    return b"".join(
        _compress_stream(data[i : i + v.block_size], v.level, v.strategy)
        for i in range(0, len(data), v.block_size)
    )


def decompress_variant(blob: bytes, variant_id: str) -> bytes:
    v = VARIANTS[variant_id]
    if v.block_size is None:
        return zlib.decompress(blob)
    out, rest = [], blob
    while rest:
        d = zlib.decompressobj()
        out.append(d.decompress(rest))
        if not d.eof:
            raise ValueError("truncated zlib segment in blocked stream")
        rest = d.unused_data
    return b"".join(out)


def alpha(data: bytes, variant_id: str) -> float:
    if not data:
        raise ValueError("empty chunk")
    return len(compress_variant(data, variant_id)) / len(data)
