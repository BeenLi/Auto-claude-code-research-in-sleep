"""Transform-aware B_crit scenarios from measured T-inverse throughput.

Thin CLI over the unit-tested closed forms in m1/profitability.py; consumes the
bf3_server host-CPU measurements (tinv_results.jsonl) and the M1.6 forward-transform
medians. Run:  PYTHONPATH=../m1 ../.m15venv/bin/python frontier_tinv.py
"""

from __future__ import annotations

import json
from pathlib import Path

import profitability as p

INF = float("inf")
GIB = 1e9  # bytes/s per GB/s
S = 2 * 1024 * 1024  # 2 MiB chunk (M2/M3 operating point)
T_FIXED = 20e-6  # s, M2 red-line budget
D_EGRESS = 23.5 * GIB  # M2 engine egress ceiling (~188 Gbps)
C_FPGA = 12.5 * GIB  # 100 Gbps FPGA compress band (M3 realistic scenario)

# Measured (2 MiB chunk, bf3_server 192-core x86 host, gcc -O3, 2026-07-06):
X_INV = {
    "bf16_chan_bt": {1: 2.04, 4: 8.15, 8: 16.18, 16: 32.30},
    "fp8_chan": {1: 1.39, 4: 5.56, 8: 11.12, 16: 22.18},
}
# Forward transform medians (single-thread numpy, myDevbox, M1.6):
X_FWD_SW = {"bf16_chan_bt": 1.45, "fp8_chan": 2.36}


def b_crit_gbps(alpha: float, *, x_fwd: float, x_inv: float) -> float:
    b = p.bandwidth_threshold_with_transform(
        alpha=alpha, C=C_FPGA, D=alpha * D_EGRESS, T_fixed=T_FIXED, S=S,
        X_fwd=x_fwd, X_inv=x_inv,
    )
    return round(b * 8 / 1e9, 1)  # bytes/s -> Gbps


def scenarios() -> dict:
    out: dict = {}
    # Reference: raw fp8_e5m2 path (no transform at all), M1 alpha
    out["fp8_e5m2_raw_no_transform"] = {"alpha": 0.732, "b_crit_gbps": b_crit_gbps(0.732, x_fwd=INF, x_inv=INF)}
    # e5m2 chan path (re-registered modern-arch alpha* = 0.704)
    for label, x_fwd in (("sw_sender", X_FWD_SW["fp8_chan"] * GIB), ("fpga_sender", INF)):
        for th, gbs in X_INV["fp8_chan"].items():
            out[f"fp8_e5m2_chan_{label}_inv{th}T"] = {
                "alpha": 0.704, "x_inv_GBps": gbs,
                "b_crit_gbps": b_crit_gbps(0.704, x_fwd=x_fwd, x_inv=gbs * GIB),
            }
    # bf16 layout path (M1.5 claimable 0.705; chan_bt inverse as conservative bound)
    out["bf16_no_transform_reference"] = {"alpha": 0.705, "b_crit_gbps": b_crit_gbps(0.705, x_fwd=INF, x_inv=INF),
                                          "note": "hypothetical free transform; bf16 RAW does not clear 0.75 at all"}
    for th, gbs in X_INV["bf16_chan_bt"].items():
        out[f"bf16_bt_fpga_sender_inv{th}T"] = {
            "alpha": 0.705, "x_inv_GBps": gbs,
            "b_crit_gbps": b_crit_gbps(0.705, x_fwd=INF, x_inv=gbs * GIB),
        }
    out["bf16_bt_sw_sender_inv8T"] = {
        "alpha": 0.705, "x_inv_GBps": X_INV["bf16_chan_bt"][8],
        "b_crit_gbps": b_crit_gbps(0.705, x_fwd=X_FWD_SW["bf16_chan_bt"] * GIB,
                                   x_inv=X_INV["bf16_chan_bt"][8] * GIB),
    }
    return out


def main() -> None:
    res = {
        "doc": "Transform-aware B_crit (Gbps, compressed-wire) at S=2MiB, C=100Gbps FPGA band, "
               "D=alpha*D_egress(188Gbps), T_fixed=20us; closed forms from m1/profitability.py "
               "(conservative additive model, no overlap).",
        "scenarios": scenarios(),
    }
    Path("tinv_frontier.json").write_text(json.dumps(res, indent=1))
    print(json.dumps(res["scenarios"], indent=1))


if __name__ == "__main__":
    main()
