"""Per-chunk layout-transform compressibility measurement (M1.6).

Reuses the canonical M1 codec matrix (``m1_codecs``) so M1.6, M1.5 and M1 can never
disagree on what "deflate" means. For one KV chunk it reports:

- ``alpha_raw``    : deflate on the raw interleaved bytes (reproduces M1).
- ``alpha_concat`` : deflate on the whole transformed buffer as ONE stream — the alpha
                     WR-ZipGuard can claim end-to-end (commodity BF3 decompresses a single
                     standard deflate stream; the receiver then inverts the permutation).
- ``transform_throughput_mbps`` : sender-side transform cost.
- ``inverse_cost_class``        : receiver-side inverse class (permutation / prefix_sum),
                                  for the profitability model's off-GPU placement check.

Bit-exactness of transform∘invert AND of the deflate roundtrip is asserted per chunk.
"""

from __future__ import annotations

import time

import layout
import m1_codecs


def _csize(data: bytes, codec: str, level) -> int:
    return len(m1_codecs.compress(data, codec, level))


def _time_transform(chunk: bytes, dtype: str, method: str, head_dim: int, warmup: int, repeats: int) -> float:
    for _ in range(max(0, warmup)):
        layout.transform(chunk, dtype, method, head_dim=head_dim)
    times = []
    for _ in range(max(1, repeats)):
        t0 = time.perf_counter_ns()
        layout.transform(chunk, dtype, method, head_dim=head_dim)
        times.append(time.perf_counter_ns() - t0)
    times.sort()
    return max(times[len(times) // 2], 1) / 1e9


def measure(
    chunk: bytes,
    dtype: str,
    method: str,
    *,
    head_dim: int,
    codec: str = "deflate",
    level=6,
    warmup: int = 1,
    repeats: int = 3,
) -> dict:
    original = len(chunk)
    if original == 0:
        raise ValueError("empty chunk")
    n = original // layout.itemsize(dtype)

    alpha_raw = _csize(chunk, codec, level) / original

    transformed = layout.transform(chunk, dtype, method, head_dim=head_dim)
    alpha_concat = _csize(transformed, codec, level) / original

    transform_s = _time_transform(chunk, dtype, method, head_dim, warmup, repeats)

    bit_exact = layout.invert(transformed, dtype, method, n, head_dim=head_dim) == chunk
    bit_exact = bit_exact and m1_codecs.decompress(
        m1_codecs.compress(transformed, codec, level), codec, level
    ) == transformed

    return {
        "dtype": dtype,
        "method": method,
        "codec": codec,
        "level": level,
        "original_size": original,
        "n_values": n,
        "head_dim": head_dim,
        "alpha_raw": alpha_raw,
        "alpha_concat": alpha_concat,
        "transform_throughput_mbps": (original / 1e6) / transform_s,
        "bit_exact": bit_exact,
        "inverse_cost_class": layout.inverse_cost_class(method),
    }
