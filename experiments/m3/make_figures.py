"""Render the M3 figures (needs matplotlib). Run where matplotlib is available (e.g. myDevbox).

    python make_figures.py --out m3_outputs
Produces:
  - figure3_frontier_heatmap.png   (analytical profitability frontier)
  - figure4_policy_comparison.png  (raw/always/static/gate transfer time vs link rate)
  - crosscheck_ttft_fit.png        (sim TTFT vs 1/link_bw, 1/bw law + fit)
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import crosscheck as cc
import frontier as fr
import plot_m3 as pm

KB, MB = 1024, 1024 * 1024
B_GRID = [5, 10, 17, 25, 50, 100, 200, 400]
S_GRID = [64 * KB, 256 * KB, 1 * MB, 2 * MB]
ALPHA = 0.732       # measured FP8_E5M2 deflate (typical)
C_FPGA = fr.gbps_to_bps(100)
T_FIXED = 5e-6


def render_frontier(out: Path) -> None:
    grid = pm.frontier_grid(B_list_gbps=B_GRID, S_list_bytes=S_GRID, alpha=ALPHA, C_bps=C_FPGA, T_fixed_s=T_FIXED)
    pm.render_frontier_heatmap(
        grid, str(out / "figure3_frontier_heatmap.png"),
        title="Figure 3 - M3 profitability frontier (FP8_E5M2 a=0.73, FPGA 100 Gbps)",
    )


def render_policy(out: Path) -> None:
    tbl = pm.policy_comparison(B_list_gbps=B_GRID, S_bytes=2 * MB, alpha=ALPHA, C_bps=C_FPGA, T_fixed_s=T_FIXED)
    pm.render_policy_comparison(
        tbl, str(out / "figure4_policy_comparison.png"),
        title="Figure 4 - policy comparison @ 2MB chunk (FP8_E5M2, FPGA 100 Gbps)",
    )


def render_crosscheck(out: Path, sweep_json: Path) -> None:  # pragma: no cover - matplotlib glue
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    data = json.loads(sweep_json.read_text())
    sweep = {float(k): float(v) for k, v in data["ttft_ns_by_link_bw"].items()}
    fit = cc.fit_transfer_model(sweep)
    A, M = fit["A_ns"], fit["M_ns_per_gbps"]

    xs = sorted(sweep)
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.scatter([1.0 / b for b in xs], [sweep[b] / 1e6 for b in xs], color="tab:blue", label="sim TTFT", zorder=3)
    line_x = [1.0 / b for b in xs]
    ax.plot(line_x, [(A + M * x) / 1e6 for x in line_x], "r--",
            label=f"fit A+M/bw  (R2={fit['r_squared']:.4f})")
    ax.axhline(cc.compute_floor_ns(sweep) / 1e6, color="gray", ls=":", label="compute floor")
    ax.set_xlabel("1 / link_bw  (s/GB)")
    ax.set_ylabel("TTFT (ms)")
    ax.set_title("Cross-check - sim PD transfer is bandwidth-limited (TTFT ~ bytes/link_bw)")
    ax.legend()
    fig.tight_layout()
    fig.savefig(str(out / "crosscheck_ttft_fit.png"), dpi=120)
    plt.close(fig)


def main() -> None:  # pragma: no cover
    p = argparse.ArgumentParser()
    p.add_argument("--out", default="m3_outputs")
    p.add_argument("--sweep-json", default="sim_sweep_result.json")
    args = p.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    render_frontier(out)
    render_policy(out)
    sweep = Path(args.sweep_json)
    if sweep.exists():
        render_crosscheck(out, sweep)
    print(f"figures written to {out}/")


if __name__ == "__main__":  # pragma: no cover
    main()
