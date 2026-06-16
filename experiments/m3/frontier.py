"""Profitability frontier: per-cell break-even physics, pure stdlib.

Each cell is one (link bandwidth B, chunk size S, compression ratio alpha, compress throughput C)
point. The decompress rate is chunk-coupled: D = alpha * D_egress(S) (see deff_curve / contract).
The break-even math itself is reused from M1 via profitability_bridge — single source of truth.
"""

from __future__ import annotations

from dataclasses import dataclass

import deff_curve as dc
from profitability_bridge import transfer_times

GBPS_TO_BPS = 1e9 / 8.0  # Gbit/s -> bytes/s
MBPS_TO_BPS = 1e6  # MB/s -> bytes/s (MB = 1e6 bytes)


def gbps_to_bps(gbps: float) -> float:
    return gbps * GBPS_TO_BPS


def mbps_to_bps(mbps: float) -> float:
    return mbps * MBPS_TO_BPS


@dataclass(frozen=True)
class Cell:
    b_gbps: float
    B_bps: float
    S_bytes: int
    alpha: float
    C_bps: float
    d_input_bps: float
    t_raw_s: float
    t_comp_s: float
    gain_s: float  # t_raw - t_comp; positive => compression pays
    profitable: bool


def evaluate_cell(*, B_bps: float, S_bytes: int, alpha: float, C_bps: float, T_fixed_s: float) -> Cell:
    """Evaluate one frontier cell. D is coupled to the chunk via alpha * D_egress(S)."""
    d_input = dc.d_input_bytes_per_s(S_bytes, alpha)
    t_raw, t_comp = transfer_times(
        alpha=alpha, B=B_bps, C=C_bps, D=d_input, T_fixed=T_fixed_s, S=S_bytes
    )
    gain = t_raw - t_comp
    return Cell(
        b_gbps=B_bps / GBPS_TO_BPS,
        B_bps=B_bps,
        S_bytes=int(S_bytes),
        alpha=alpha,
        C_bps=C_bps,
        d_input_bps=d_input,
        t_raw_s=t_raw,
        t_comp_s=t_comp,
        gain_s=gain,
        profitable=t_comp < t_raw,
    )


def sweep(
    *, B_list_gbps: list[float], S_list_bytes: list[int], alpha: float, C_bps: float, T_fixed_s: float
) -> list[Cell]:
    """Evaluate the full B x S grid at one (alpha, C)."""
    return [
        evaluate_cell(B_bps=gbps_to_bps(b), S_bytes=s, alpha=alpha, C_bps=C_bps, T_fixed_s=T_fixed_s)
        for b in B_list_gbps
        for s in S_list_bytes
    ]
