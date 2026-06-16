"""M2 BF3 decompress-throughput curve D_eff(chunk), pure stdlib.

The measured M2 points are EGRESS (decompressed-output) Gbps. ``profitability.py`` models the
decompress term as ``alpha*S/D`` where D consumes COMPRESSED-INPUT bytes, so the frontier must feed
``D = alpha * d_egress`` (see EVALUATION_CONTRACT_M3.md, "Units reconciliation"). This module exposes
the egress curve plus the input-rate conversion and the amortization gate.

Interpolation is piecewise-linear in log2(chunk_bytes) between measured points (the curve is
concave/saturating), clamped to the data range at both ends — no extrapolation past what M2 measured.
"""

from __future__ import annotations

import json
from math import log2
from pathlib import Path

GBPS_TO_BPS = 1e9 / 8.0  # Gbit/s -> bytes/s

_INPUTS = json.loads((Path(__file__).resolve().parent / "measured_inputs.json").read_text())
_DECOMP = _INPUTS["decompress"]

# {chunk_bytes: egress Gbps}, sorted by chunk size.
_POINTS = sorted(
    (int(k), float(v)) for k, v in _DECOMP["d_egress_gbps_by_chunk_bytes"].items()
)
MIN_CHUNK_BYTES = int(_DECOMP["min_chunk_bytes"])
MAX_TESTED_CHUNK_BYTES = int(_DECOMP["max_tested_chunk_bytes"])


def d_egress_gbps(chunk_bytes: float) -> float:
    """Decompressed-output throughput (Gbps) for a chunk of ``chunk_bytes`` original bytes."""
    if chunk_bytes <= 0:
        raise ValueError(f"chunk_bytes must be > 0, got {chunk_bytes}")
    lo_c, lo_v = _POINTS[0]
    hi_c, hi_v = _POINTS[-1]
    if chunk_bytes <= lo_c:
        return lo_v  # clamp: no extrapolation below the data
    if chunk_bytes >= hi_c:
        return hi_v  # clamp: hold the measured ceiling above the data
    for (c0, v0), (c1, v1) in zip(_POINTS, _POINTS[1:]):
        if c0 <= chunk_bytes <= c1:
            t = (log2(chunk_bytes) - log2(c0)) / (log2(c1) - log2(c0))
            return v0 + t * (v1 - v0)
    raise AssertionError("unreachable")  # pragma: no cover


def d_egress_bytes_per_s(chunk_bytes: float) -> float:
    """Egress throughput in bytes/second."""
    return d_egress_gbps(chunk_bytes) * GBPS_TO_BPS


def d_input_bytes_per_s(chunk_bytes: float, alpha: float) -> float:
    """Decompress INPUT-consumption rate (bytes/s) = the D for profitability.py.

    Decompress reads ``alpha*S`` compressed bytes and writes ``S`` egress bytes in the same time,
    so ``D_input = alpha * D_egress``.
    """
    return alpha * d_egress_bytes_per_s(chunk_bytes)


def is_amortized(chunk_bytes: float) -> bool:
    """True iff the chunk is large enough (>= 256 KB) to amortize the M2 fixed per-task cost."""
    return chunk_bytes >= MIN_CHUNK_BYTES


def is_within_tested_range(chunk_bytes: float) -> bool:
    """True iff the chunk is within the M2-tested range (<= 2 MB/task)."""
    return chunk_bytes <= MAX_TESTED_CHUNK_BYTES
