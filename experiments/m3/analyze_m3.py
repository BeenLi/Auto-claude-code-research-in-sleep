"""M3 go/no-go: profitable-region detection + GREEN/YELLOW/RED verdict (pure stdlib).

The decisive quantity is the *critical bandwidth* B_crit(S, alpha, C): the link rate below which
per-WR compression beats raw. It is found by bisection over the same ``frontier.evaluate_cell`` the
rest of M3 uses (no separate formula to drift). The verdict classifies the region against a
mainstream-datacenter link-rate threshold.
"""

from __future__ import annotations

import json
from pathlib import Path

import frontier as fr

GBPS_TO_BPS = fr.GBPS_TO_BPS

# A profitable region that reaches mainstream per-flow datacenter rates (>= this) is GREEN; a region
# that exists only below it is a narrow, bandwidth-limited window (cross-AZ / oversubscribed) = YELLOW.
DATACENTER_GBPS = 100.0

_INPUTS = json.loads((Path(__file__).resolve().parent / "measured_inputs.json").read_text())


def _profitable_at(B_gbps: float, *, S_bytes: int, alpha: float, C_bps: float, T_fixed_s: float) -> bool:
    return fr.evaluate_cell(
        B_bps=fr.gbps_to_bps(B_gbps), S_bytes=S_bytes, alpha=alpha, C_bps=C_bps, T_fixed_s=T_fixed_s
    ).profitable


def b_crit_gbps(
    *, S_bytes: int, alpha: float, C_bps: float, T_fixed_s: float, hi_gbps: float = 1e6, tol_gbps: float = 1e-3
) -> float:
    """Largest link rate (Gbps) at which compression still pays. 0.0 if no profitable region.

    Profitability is monotone in B (lower B => more profitable), so bisect the True/False boundary.
    """
    lo = 1e-9  # an essentially-zero link rate: the most favorable case for compression
    if not _profitable_at(lo, S_bytes=S_bytes, alpha=alpha, C_bps=C_bps, T_fixed_s=T_fixed_s):
        return 0.0  # never profitable, even at vanishing bandwidth
    hi = hi_gbps
    if _profitable_at(hi, S_bytes=S_bytes, alpha=alpha, C_bps=C_bps, T_fixed_s=T_fixed_s):
        return hi  # profitable everywhere in range (degenerate; not expected with finite D)
    while hi - lo > tol_gbps:
        mid = 0.5 * (lo + hi)
        if _profitable_at(mid, S_bytes=S_bytes, alpha=alpha, C_bps=C_bps, T_fixed_s=T_fixed_s):
            lo = mid
        else:
            hi = mid
    return lo


def verdict(
    *, alpha: float, C_band_gbps: list[float], chunk_bytes: int, T_fixed_s: float
) -> dict:
    """Classify the profitable region for one (alpha, chunk) across a compress-throughput band.

    region_max_gbps = B_crit at the *best* (fastest) compressor in the band — the most generous
    profitable bandwidth the envelope can justify.
    """
    per_c = {
        c: b_crit_gbps(S_bytes=chunk_bytes, alpha=alpha, C_bps=fr.gbps_to_bps(c), T_fixed_s=T_fixed_s)
        for c in C_band_gbps
    }
    region_max = max(per_c.values())

    if region_max <= 0.0:
        label = "RED"
        rationale = (
            f"No profitable region: at alpha={alpha} and chunk={chunk_bytes}B, compression never "
            f"beats raw at any link rate across the compress band {C_band_gbps} Gbps. "
            f"Pivot to the negative-result / profitability-atlas paper."
        )
    elif region_max >= DATACENTER_GBPS:
        label = "GREEN"
        rationale = (
            f"Profitable region reaches mainstream datacenter rates: compression pays for "
            f"B < {region_max:.1f} Gbps (>= {DATACENTER_GBPS:.0f} Gbps threshold) at alpha={alpha}, "
            f"chunk={chunk_bytes}B."
        )
    else:
        label = "YELLOW"
        rationale = (
            f"Narrow, bandwidth-limited region: compression pays only for B < {region_max:.1f} Gbps "
            f"(below the {DATACENTER_GBPS:.0f} Gbps mainstream threshold) at alpha={alpha}, "
            f"chunk={chunk_bytes}B. Profitable for cross-AZ / oversubscribed fabrics; proceed but "
            f"flag the narrow window. Caveat: the ~188 Gbps D_egress ceiling may be PCIe-x8-limited, "
            f"so the true window could be ~2x wider on x16 / DPU-local memory."
        )

    return {
        "verdict": label,
        "region_max_gbps": region_max,
        "b_crit_by_compress_gbps": per_c,
        "alpha": alpha,
        "chunk_bytes": chunk_bytes,
        "datacenter_threshold_gbps": DATACENTER_GBPS,
        "rationale": rationale,
    }


def verdict_for_measured_envelope() -> dict:
    """The headline M3 verdict using the committed measured envelope (typical alpha, FPGA band, 2MB)."""
    comp = _INPUTS["compression"]["alpha"]
    fpga = _INPUTS["compress_band"]["fpga"]["band_gbps"]
    chunk = _INPUTS["decompress"]["max_tested_chunk_bytes"]
    t_fixed = _INPUTS["decompress"]["t_fixed_s"]
    return verdict(alpha=comp["typical"], C_band_gbps=fpga, chunk_bytes=chunk, T_fixed_s=t_fixed)


def main() -> None:  # pragma: no cover
    import argparse

    parser = argparse.ArgumentParser(description="M3 analytical frontier go/no-go verdict.")
    parser.add_argument("--out", type=str, default=None, help="write the verdict JSON here")
    args = parser.parse_args()

    v = verdict_for_measured_envelope()
    print(json.dumps(v, indent=2))
    if args.out:
        Path(args.out).write_text(json.dumps(v, indent=2))


if __name__ == "__main__":  # pragma: no cover
    main()
