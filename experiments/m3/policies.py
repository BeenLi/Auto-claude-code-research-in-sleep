"""The four compared transfer policies and their per-chunk outcomes (pure stdlib).

- raw      : never compress (the core baseline, alpha = 1).
- always   : compress every chunk (straw-man upper bound).
- static   : compress iff chunk >= static_threshold_bytes (KVServe/SplitZip-style heuristic).
- gate     : WR-ZipGuard — compress iff the chunk is actually profitable (per-WR break-even).
"""

from __future__ import annotations

from dataclasses import dataclass

import deff_curve as dc
from frontier import evaluate_cell

POLICIES = ("raw", "always", "static", "gate")

DEFAULT_STATIC_THRESHOLD_BYTES = dc.MIN_CHUNK_BYTES  # 256 KB amortization gate


def decide(
    policy: str,
    *,
    alpha: float,
    B_bps: float,
    C_bps: float,
    S_bytes: int,
    T_fixed_s: float,
    static_threshold_bytes: int = DEFAULT_STATIC_THRESHOLD_BYTES,
) -> bool:
    """Return True iff ``policy`` compresses this chunk."""
    if policy == "raw":
        return False
    if policy == "always":
        return True
    if policy == "static":
        return S_bytes >= static_threshold_bytes
    if policy == "gate":
        return evaluate_cell(
            B_bps=B_bps, S_bytes=S_bytes, alpha=alpha, C_bps=C_bps, T_fixed_s=T_fixed_s
        ).profitable
    raise ValueError(f"unknown policy {policy!r}; expected one of {POLICIES}")


@dataclass(frozen=True)
class Outcome:
    policy: str
    compressed: bool
    bytes_on_wire: float
    transfer_time_s: float


def outcome(
    policy: str,
    *,
    alpha: float,
    B_bps: float,
    C_bps: float,
    S_bytes: int,
    T_fixed_s: float,
    static_threshold_bytes: int = DEFAULT_STATIC_THRESHOLD_BYTES,
) -> Outcome:
    """Realized bytes-on-wire and transfer time for ``policy`` on one chunk.

    A policy that compresses pays the compressed-path time whether or not it was profitable; a
    policy that does not compress pays the raw time. This is what makes always-compress lose to raw
    in the no-gain regime.
    """
    compressed = decide(
        policy, alpha=alpha, B_bps=B_bps, C_bps=C_bps, S_bytes=S_bytes,
        T_fixed_s=T_fixed_s, static_threshold_bytes=static_threshold_bytes,
    )
    cell = evaluate_cell(B_bps=B_bps, S_bytes=S_bytes, alpha=alpha, C_bps=C_bps, T_fixed_s=T_fixed_s)
    if compressed:
        return Outcome(policy, True, alpha * S_bytes, cell.t_comp_s)
    return Outcome(policy, False, float(S_bytes), cell.t_raw_s)
